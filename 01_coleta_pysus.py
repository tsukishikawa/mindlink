"""
╔════════════════════════════════════════════════════════════╗
║  MindLink — Coleta SIH-SUS via PySUS                       ║
║  CID-10 F00–F03 + G30 · São Paulo · Sprint 3                ║
║  Núcleo metodológico: DIAG_PRINC vs DIAG_PRINC+DIAG_SECUN   ║
╚════════════════════════════════════════════════════════════╝

Objetivo da Sprint 3
--------------------
Sair do CSV/manual/simulado e criar uma base auditável a partir do SIH-SUS
via PySUS. O CSV existe apenas como produto intermediário do pipeline para
facilitar evidências, importação no SQL Developer e entrega da Rita.

Fluxo:
    DATASUS/SIH-SUS → PySUS → pandas → parquet/csv tratado → Oracle

Instalação:
    pip install --upgrade "pysus>=2.0" pandas pyarrow

Uso rápido:
    python 01_coleta_pysus.py

Configuração por variável de ambiente, se quiser testar recortes menores:
    MINDLINK_UF=SP
    MINDLINK_ANOS=2024
    MINDLINK_MESES=1
    MINDLINK_MUNICIPIO=3550308   # opcional; vazio = estado inteiro
"""

from __future__ import annotations

import os
import warnings
from typing import Iterable

import pandas as pd

warnings.filterwarnings("ignore")

# ── Configurações ────────────────────────────────────────────────────────────
UF = os.getenv("MINDLINK_UF", "SP").upper()
MUNICIPIO = os.getenv("MINDLINK_MUNICIPIO", "").strip() or None
# Use default leve para primeira evidência. Para entrega final: MINDLINK_ANOS=2020,2021,2022,2023,2024,2025
ANOS = [int(x) for x in os.getenv("MINDLINK_ANOS", "2024").split(",") if x.strip()]
MESES = [int(x) for x in os.getenv("MINDLINK_MESES", "1").split(",") if x.strip()]
GRUPO = os.getenv("MINDLINK_SIH_GRUPO", "RD")  # RD = AIH reduzida

OUTPUT_RAW = "data/raw/"
OUTPUT_PROC = "data/processed/"
os.makedirs(OUTPUT_RAW, exist_ok=True)
os.makedirs(OUTPUT_PROC, exist_ok=True)
os.environ.setdefault("PYSUS_CACHEPATH", os.path.abspath(OUTPUT_RAW))

# CIDs de demência — recorte clínico oficial do projeto.
CIDS_DEMENCIA = ("F00", "F01", "F02", "F03", "G30")

LABEL_CID = {
    "F00": "Alzheimer (F00)",
    "F01": "Demência vascular",
    "F02": "Demência por outras doenças",
    "F03": "Demência não especificada",
    "G30": "Doença de Alzheimer (G30)",
}


def _normalizar_codigo(valor: object) -> str:
    """Normaliza códigos CID/município evitando perda de zeros à esquerda."""
    if pd.isna(valor):
        return ""
    return str(valor).strip().upper()


def _colunas_secundarias(df: pd.DataFrame) -> list[str]:
    """Detecta possíveis colunas de diagnóstico secundário no SIH/SUS.

    Em algumas versões/exportações aparecem nomes como DIAG_SECUN; em outras,
    DIAGSEC1, DIAGSEC2... Por isso a detecção é propositalmente tolerante.
    """
    candidatas = []
    for col in df.columns:
        c = col.upper().replace(" ", "").replace("-", "_")
        if c in {"DIAG_SECUN", "DIAGSECUN", "DIAG_SECUNDARIO"}:
            candidatas.append(col)
        elif c.startswith("DIAGSEC") or c.startswith("DIAG_SEC"):
            if c != "DIAG_PRINC":
                candidatas.append(col)
    # Remove duplicatas preservando ordem
    return list(dict.fromkeys(candidatas))


def _mask_cid_demencia(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.upper().str.strip().str.startswith(CIDS_DEMENCIA, na=False)


def _primeiro_cid_demencia(row: pd.Series, cols: Iterable[str]) -> str | None:
    for col in cols:
        cid = _normalizar_codigo(row.get(col))
        if cid.startswith(CIDS_DEMENCIA):
            return cid[:3]
    return None


# ── Coleta via PySUS ─────────────────────────────────────────────────────────
def coletar_sih_pysus(uf: str, anos: list[int], meses: list[int]) -> pd.DataFrame:
    """Baixa arquivos RD do SIH-SUS via PySUS 2.x."""
    try:
        import pysus
    except ImportError as exc:
        raise ImportError('Execute: pip install --upgrade "pysus>=2.0"') from exc

    print("=" * 72)
    print("MINDLINK — COLETA SIH/SUS VIA PySUS")
    print("=" * 72)
    print(f"UF={uf} · anos={anos} · meses={meses} · grupo={GRUPO}")

    df_raw = pysus.sih(
        state=uf,
        year=anos,
        month=meses,
        group=GRUPO,
        as_dataframe=True,
        show_progress=True,
    )

    if df_raw is None or df_raw.empty:
        raise RuntimeError("Nenhum registro carregado. Verifique PySUS, conexão e parâmetros.")

    print(f"[PySUS] Total bruto: {len(df_raw):,} linhas · {len(df_raw.columns)} colunas")
    print("[PySUS] Colunas disponíveis:")
    print(", ".join(df_raw.columns.astype(str).tolist()))
    return df_raw


# ── Filtro metodológico principal ────────────────────────────────────────────
def filtrar_demencia(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compara DIAG_PRINC vs DIAG_SECUN e retorna a base final de demência.

    Saídas:
      1. df_dem: registros onde demência aparece no diagnóstico principal OU secundário
      2. comparativo: tabela com contagens por modo de detecção
    """
    if "DIAG_PRINC" not in df.columns:
        raise ValueError("Coluna DIAG_PRINC não encontrada. Confirme se o grupo SIH é RD.")

    sec_cols = _colunas_secundarias(df)
    print(f"[Diagnóstico] Colunas secundárias detectadas: {sec_cols if sec_cols else 'nenhuma'}")

    mask_principal = _mask_cid_demencia(df["DIAG_PRINC"])

    if sec_cols:
        mask_secundario = pd.Series(False, index=df.index)
        for col in sec_cols:
            mask_secundario = mask_secundario | _mask_cid_demencia(df[col])
    else:
        mask_secundario = pd.Series(False, index=df.index)

    # Comparativo que será evidência da tese metodológica.
    total = len(df)
    n_principal = int(mask_principal.sum())
    n_secundario = int(mask_secundario.sum())
    n_qualquer = int((mask_principal | mask_secundario).sum())
    ganho = n_qualquer - n_principal
    ganho_pct = (ganho / n_qualquer * 100) if n_qualquer else 0

    comparativo = pd.DataFrame([
        {"modo_filtro": "DIAG_PRINC", "internacoes": n_principal, "percentual_total": round(n_principal / total * 100, 4)},
        {"modo_filtro": "DIAG_SECUN", "internacoes": n_secundario, "percentual_total": round(n_secundario / total * 100, 4)},
        {"modo_filtro": "DIAG_PRINC + DIAG_SECUN", "internacoes": n_qualquer, "percentual_total": round(n_qualquer / total * 100, 4)},
    ])

    print("\n[Comparativo metodológico]")
    print(comparativo.to_string(index=False))
    print(f"\n[Achado] Usar também DIAG_SECUN adiciona {ganho:,} registros ({ganho_pct:.1f}% da base detectada).")

    df_dem = df[mask_principal | mask_secundario].copy()
    df_dem["demencia_principal"] = mask_principal.loc[df_dem.index].astype(int)
    df_dem["demencia_secundaria"] = mask_secundario.loc[df_dem.index].astype(int)
    df_dem["demencia_em"] = "principal"
    df_dem.loc[(df_dem["demencia_principal"] == 0) & (df_dem["demencia_secundaria"] == 1), "demencia_em"] = "secundaria"
    df_dem.loc[(df_dem["demencia_principal"] == 1) & (df_dem["demencia_secundaria"] == 1), "demencia_em"] = "principal_secundaria"

    df_dem["cid_grupo_principal"] = df_dem["DIAG_PRINC"].astype(str).str[:3].str.upper()
    df_dem["cid_demencia_detectado"] = df_dem["cid_grupo_principal"].where(
        df_dem["cid_grupo_principal"].str.startswith(CIDS_DEMENCIA, na=False)
    )
    if sec_cols:
        df_dem.loc[df_dem["cid_demencia_detectado"].isna(), "cid_demencia_detectado"] = df_dem.loc[
            df_dem["cid_demencia_detectado"].isna()
        ].apply(lambda r: _primeiro_cid_demencia(r, sec_cols), axis=1)
        df_dem["cid_secundario_detectado"] = df_dem.apply(lambda r: _primeiro_cid_demencia(r, sec_cols), axis=1)
    else:
        df_dem["cid_secundario_detectado"] = None

    if MUNICIPIO and "MUNIC_RES" in df_dem.columns:
        antes = len(df_dem)
        prefixo = MUNICIPIO[:6]
        df_dem = df_dem[df_dem["MUNIC_RES"].astype(str).str[:6] == prefixo].copy()
        print(f"[Município] Filtro {MUNICIPIO}: {antes:,} → {len(df_dem):,} registros")

    return df_dem, comparativo


# ── Limpeza e enriquecimento ─────────────────────────────────────────────────
def processar(df: pd.DataFrame) -> pd.DataFrame:
    """Seleciona e renomeia campos para o esquema analítico da Sprint 3."""
    colunas = {
        "DIAG_PRINC": "cid_principal",
        "cid_secundario_detectado": "cid_secundario",
        "cid_demencia_detectado": "cid_demencia_detectado",
        "cid_grupo_principal": "cid_grupo_principal",
        "demencia_em": "demencia_em",
        "demencia_principal": "demencia_principal",
        "demencia_secundaria": "demencia_secundaria",
        "MUNIC_RES": "municipio_residencia",
        "MUNIC_MOV": "municipio_internacao",
        "IDADE": "idade",
        "SEXO": "sexo",
        "DIAS_PERM": "dias_permanencia",
        "VAL_TOT": "valor_total",
        "MORTE": "obito",
        "ANO_CMPT": "ano",
        "MES_CMPT": "mes",
        "CNES": "cnes_hospital",
        "N_AIH": "n_aih",
    }
    existentes = {k: v for k, v in colunas.items() if k in df.columns}
    out = df.rename(columns=existentes)[list(existentes.values())].copy()

    if "cid_demencia_detectado" in out.columns:
        out["cid_label"] = out["cid_demencia_detectado"].map(LABEL_CID)

    if "sexo" in out.columns:
        out["sexo"] = out["sexo"].astype(str).str.strip()
        out["sexo_label"] = out["sexo"].map({"1": "Masculino", "3": "Feminino"}).fillna("Ignorado")

    if "idade" in out.columns:
        out["idade"] = pd.to_numeric(out["idade"], errors="coerce")
        out["faixa_etaria"] = pd.cut(
            out["idade"],
            bins=[-1, 59, 69, 74, 79, 84, 200],
            labels=["<60", "60-69", "70-74", "75-79", "80-84", "85+"],
            right=True,
        ).astype("object")

    for c in ("ano", "mes", "dias_permanencia", "valor_total", "obito"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    for c in ("municipio_residencia", "municipio_internacao", "cnes_hospital"):
        if c in out.columns:
            out[c] = out[c].astype(str).str.strip()

    print(f"\n[Processamento] {len(out):,} linhas · {len(out.columns)} colunas finais")
    return out


# ── Pipeline principal ───────────────────────────────────────────────────────
def main() -> None:
    df_raw = coletar_sih_pysus(UF, ANOS, MESES)
    df_dem, comparativo = filtrar_demencia(df_raw)
    df_final = processar(df_dem)

    parquet_final = os.path.join(OUTPUT_PROC, "mindlink_internacoes_sp.parquet")
    csv_final = os.path.join(OUTPUT_PROC, "mindlink_internacoes_sp.csv")
    parquet_compat = os.path.join(OUTPUT_PROC, "mindlink_demencia_sp.parquet")  # compatibilidade com scripts antigos
    csv_comparativo = os.path.join(OUTPUT_PROC, "comparativo_filtro_demencia.csv")

    df_final.to_parquet(parquet_final, index=False)
    df_final.to_parquet(parquet_compat, index=False)
    df_final.to_csv(csv_final, index=False)
    comparativo.to_csv(csv_comparativo, index=False)

    print("\n✓ Arquivos gerados:")
    print(f"  - {parquet_final}")
    print(f"  - {csv_final}")
    print(f"  - {csv_comparativo}")
    print("\n[Preview]")
    print(df_final.head().to_string(index=False))


if __name__ == "__main__":
    main()
