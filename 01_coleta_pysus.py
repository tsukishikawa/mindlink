"""
╔════════════════════════════════════════════════════════════╗
║  MindLink — Coleta SIH-SUS via PySUS                       ║
║  CID-10 F00–F03 + G30 (Demência) · SP-município · 2020–2025 ║
║  Base observada para projeção nacional (Equipe She Leads)   ║
╚════════════════════════════════════════════════════════════╝

Instalação:
    pip install --upgrade "pysus>=2.0" pandas pyarrow

Uso:
    python 01_coleta_pysus.py
"""

import os
import warnings
import pandas as pd

warnings.filterwarnings("ignore")

# ── Configurações ────────────────────────────────────────────────────────────
UF            = "SP"                        # estado baixado do FTP
MUNICIPIO     = "355030"                    # São Paulo capital (base observada do deck)
                                            # use None para coletar o estado inteiro (Sprint 3)
ANOS          = list(range(2020, 2026))     # histórico 2020–2025 (workbook do deck)
MESES         = list(range(1, 13))          # ano cheio (Jan–Dez) — obrigatório na 2.x
GRUPO         = "RD"                         # RD = Reduzida de AIH
OUTPUT_RAW    = "data/raw/"
OUTPUT_PROC   = "data/processed/"

# IMPORTANTE: o pysus 2.x lê o caminho do cache no momento do import.
# Por isso definimos PYSUS_CACHEPATH ANTES de importar o pacote, lá embaixo.
os.makedirs(OUTPUT_RAW, exist_ok=True)
os.makedirs(OUTPUT_PROC, exist_ok=True)
os.environ.setdefault("PYSUS_CACHEPATH", os.path.abspath(OUTPUT_RAW))

# CIDs de demência — F00–F03 (cap. V) + G30 (cap. VI, doença de Alzheimer).
# O deck define o recorte como "F00-F03 + G30". DIAG_SECUN (comorbidade)
# fica para a Sprint 3 — ver nota em filtrar_demencia().
CIDS_DEMENCIA = (
    "F00",  # Demência na doença de Alzheimer
    "F01",  # Demência vascular
    "F02",  # Demência em outras doenças
    "F03",  # Demência não especificada
    "G30",  # Doença de Alzheimer (capítulo VI)
)

# Mapeamento de nomes amigáveis por CID
LABEL_CID = {
    "F00": "Alzheimer (F00)",
    "F01": "Demência Vascular",
    "F02": "Demência por outras doenças",
    "F03": "Demência não especificada",
    "G30": "Doença de Alzheimer (G30)",
}


# ── Coleta via PySUS (API 2.x) ───────────────────────────────────────────────
def coletar_sih_pysus(uf: str, anos: list, meses: list) -> pd.DataFrame:
    """
    Baixa arquivos RD do SIH-SUS via PySUS 2.x.
    RD = Reduzida de AIH (Autorização de Internação Hospitalar).
    Contém: diagnóstico, município, permanência, custo, idade, sexo.

    Na 2.x uma única chamada já consulta o FTP do DATASUS, baixa os
    arquivos em paralelo (com barra de progresso) e concatena tudo
    num DataFrame quando as_dataframe=True.
    """
    try:
        import pysus
    except ImportError:
        raise ImportError('Execute: pip install --upgrade "pysus>=2.0"')

    print(f"[PySUS] Baixando grupo {GRUPO} do SIH-SUS — UF={uf}, "
          f"anos={anos[0]}–{anos[-1]}, {len(meses)} mês(es)/ano...")

    df_raw = pysus.sih(
        state=uf,
        year=anos,
        month=meses,
        group=GRUPO,
        as_dataframe=True,    # concatena tudo num DataFrame
        show_progress=True,   # barra de progresso (tqdm)
    )

    if df_raw is None or df_raw.empty:
        raise RuntimeError(
            "Nenhum arquivo carregado. Verifique UF/anos/meses e a conexão "
            "com o FTP do DATASUS."
        )

    print(f"\n[PySUS] Total bruto: {len(df_raw):,} internações em "
          f"{uf} ({anos[0]}–{anos[-1]})")
    return df_raw


# ── Filtro por CID (inalterado) ──────────────────────────────────────────────
def filtrar_demencia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mantém apenas registros com DIAG_PRINC começando em F00, F01, F02 ou F03.
    Inclui subtipos: F000, F001, F009, F010, F011 ... F03, etc.
    """
    if "DIAG_PRINC" not in df.columns:
        raise ValueError("Coluna DIAG_PRINC não encontrada. Verifique os arquivos RD.")

    mask = df["DIAG_PRINC"].astype(str).str.upper().str.startswith(CIDS_DEMENCIA, na=False)
    df_dem = df[mask].copy()

    # Recorte SP-município (base observada do deck). DIAG_SECUN (demência como
    # comorbidade) é o achado da Sprint 3 — a literatura indica subnotificação
    # de 8-10x ao usar só DIAG_PRINC. Para ativar, una um segundo mask sobre
    # DIAG_SECUN aqui.
    if MUNICIPIO and "MUNIC_RES" in df_dem.columns:
        antes = len(df_dem)
        df_dem = df_dem[df_dem["MUNIC_RES"].astype(str).str[:6] == MUNICIPIO].copy()
        print(f"[Município] Filtro {MUNICIPIO} (SP capital): "
              f"{antes:,} → {len(df_dem):,} internações")

    pct = len(df_dem) / len(df) * 100 if len(df) else 0
    print(f"\n[Filtro] Demência (F00–F03 + G30): {len(df_dem):,} internações "
          f"({pct:.3f}% do total {UF})")

    # Distribuição por CID grupo
    df_dem["cid_grupo"] = df_dem["DIAG_PRINC"].astype(str).str[:3].str.upper()
    print("\n  Distribuição por CID:")
    for cid, label in LABEL_CID.items():
        n = (df_dem["cid_grupo"] == cid).sum()
        print(f"    {cid} ({label}): {n:,}")

    return df_dem


# ── Limpeza e enriquecimento ─────────────────────────────────────────────────
def processar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Seleciona, renomeia e enriquece os campos do SIH-SUS já no esquema
    final consumido pelo modelo (02) e pela ingestão Oracle (03):

        cid_principal · cid_grupo · cid_label · ano · mes · sexo · sexo_label
        · idade · faixa_etaria · municipio_residencia · dias_permanencia
        · valor_total · cnes_hospital · obito

    Os nomes já saem alinhados (ano/mes, cid_grupo, sexo_label), então
    os scripts 02 e 03 não precisam mais normalizar nada.
    """
    # Campos da AIH-RD → nomes finais (mantém só o que existir no DataFrame)
    colunas = {
        "DIAG_PRINC": "cid_principal",
        "MUNIC_RES":  "municipio_residencia",
        "IDADE":      "idade",
        "SEXO":       "sexo",
        "DIAS_PERM":  "dias_permanencia",
        "VAL_TOT":    "valor_total",
        "MORTE":      "obito",
        "ANO_CMPT":   "ano",
        "MES_CMPT":   "mes",
        "CNES":       "cnes_hospital",
    }
    existentes = {k: v for k, v in colunas.items() if k in df.columns}
    out = df.rename(columns=existentes)[list(existentes.values())].copy()

    # cid_grupo (calculado em filtrar_demencia) + label amigável
    if "cid_grupo" in df.columns:
        out["cid_grupo"] = df["cid_grupo"]
        out["cid_label"] = out["cid_grupo"].map(LABEL_CID)

    # sexo_label (no SIH: 1 = Masculino, 3 = Feminino)
    if "sexo" in out.columns:
        out["sexo_label"] = out["sexo"].astype(str).map({"1": "Masculino", "3": "Feminino"})

    # Faixa etária (mesmos rótulos usados no dashboard e nas views)
    if "idade" in out.columns:
        out["idade"] = pd.to_numeric(out["idade"], errors="coerce")
        out["faixa_etaria"] = pd.cut(
            out["idade"],
            bins=[0, 59, 69, 74, 79, 84, 200],
            labels=["<60", "60-69", "70-74", "75-79", "80-84", "85+"],
            right=True,
        ).astype("object")

    # ano/mes como inteiro
    for c in ("ano", "mes"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64")

    # Tipagem numérica de custo/permanência
    for c in ("valor_total", "dias_permanencia"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    print(f"\n[Processamento] {len(out):,} linhas · {len(out.columns)} colunas finais")
    return out


# ── Pipeline principal ───────────────────────────────────────────────────────
def main():
    df_raw = coletar_sih_pysus(UF, ANOS, MESES)
    df_dem = filtrar_demencia(df_raw)
    df_final = processar(df_dem)

    destino = os.path.join(OUTPUT_PROC, "mindlink_demencia_sp.parquet")
    df_final.to_parquet(destino, index=False)
    print(f"\n✓ Salvo em: {destino}")
    print(df_final.head())


if __name__ == "__main__":
    main()