"""
MindLink — Coleta CNES via PySUS
Sprint 3: capacidade hospitalar para cálculo de pressão assistencial.

Objetivo:
    Baixar dados CNES de leitos/unidades e gerar uma base padronizada para
    integrar com SIH/SUS no Oracle.

Saída:
    data/processed/capacidade_cnes_sp.csv

Observação:
    O grupo CNES de leitos costuma ser "LT". Caso o PySUS retorne nomes de
    colunas diferentes, o script salva as colunas disponíveis e mostra o preview
    para ajuste fino.
"""

from __future__ import annotations

import os
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

UF = os.getenv("MINDLINK_UF", "SP").upper()
ANOS = [int(x) for x in os.getenv("MINDLINK_CNES_ANOS", "2024").split(",") if x.strip()]
MESES = [int(x) for x in os.getenv("MINDLINK_CNES_MESES", "1").split(",") if x.strip()]
GRUPO = os.getenv("MINDLINK_CNES_GRUPO", "LT")  # LT = leitos, em geral

OUTPUT_RAW = "data/raw/"
OUTPUT_PROC = "data/processed/"
os.makedirs(OUTPUT_RAW, exist_ok=True)
os.makedirs(OUTPUT_PROC, exist_ok=True)
os.environ.setdefault("PYSUS_CACHEPATH", os.path.abspath(OUTPUT_RAW))


def _normalizar_coluna(col: str) -> str:
    return col.upper().replace(" ", "_").replace("-", "_")


def _achar_coluna(df: pd.DataFrame, nomes: list[str]) -> str | None:
    mapa = {_normalizar_coluna(c): c for c in df.columns}
    for nome in nomes:
        if _normalizar_coluna(nome) in mapa:
            return mapa[_normalizar_coluna(nome)]
    return None


def coletar_cnes() -> pd.DataFrame:
    try:
        import pysus
    except ImportError as exc:
        raise ImportError('Execute: pip install --upgrade "pysus>=2.0"') from exc

    print("=" * 72)
    print("MINDLINK — COLETA CNES VIA PySUS")
    print("=" * 72)
    print(f"UF={UF} · anos={ANOS} · meses={MESES} · grupo={GRUPO}")

    df = pysus.cnes(
        state=UF,
        year=ANOS,
        month=MESES,
        group=GRUPO,
        as_dataframe=True,
        show_progress=True,
    )

    if df is None or df.empty:
        raise RuntimeError("Nenhum registro CNES carregado. Verifique grupo, período e conexão.")

    print(f"[CNES] Total bruto: {len(df):,} linhas · {len(df.columns)} colunas")
    print("[CNES] Colunas disponíveis:")
    print(", ".join(df.columns.astype(str).tolist()))
    return df


def processar_cnes(df: pd.DataFrame) -> pd.DataFrame:
    candidatos = {
        "ano": ["ANO", "ANO_CMPT", "COMPETENCIA_ANO", "COMP"],
        "mes": ["MES", "MES_CMPT", "COMPETENCIA_MES", "COMP"],
        "uf": ["UF", "SIGLA_UF"],
        "municipio": ["MUNICIPIO", "CODUFMUN", "MUN", "COD_MUNICIPIO"],
        "cnes": ["CNES", "CO_CNES"],
        "nome_estabelecimento": ["NOME_ESTABELECIMENTO", "NO_FANTASIA", "NOME", "NO_RAZAO_SOCIAL"],
        "tipo_unidade": ["DS_TIPO_UNIDADE", "TIPO_UNIDADE", "TP_UNIDADE"],
        "leitos_existentes": ["LEITOS_EXISTENTE", "QT_EXIST", "QT_EXISTENTE", "QTLEITP1"],
        "leitos_sus": ["LEITOS_SUS", "QT_SUS", "QTLEITP2"],
        "uti_existente": ["UTI_TOTAL_EXIST", "UTI_TOTAL_EXISTENTE", "UTI_EXISTENTE"],
        "uti_sus": ["UTI_TOTAL_SUS", "UTI_SUS"],
    }

    out = pd.DataFrame()
    for destino, nomes in candidatos.items():
        col = _achar_coluna(df, nomes)
        if col:
            out[destino] = df[col]
        else:
            out[destino] = None

    # Se COMP vier no formato YYYYMM, tenta extrair ano/mês.
    if out["ano"].isna().all() and _achar_coluna(df, ["COMP"]):
        comp = df[_achar_coluna(df, ["COMP"])].astype(str).str.extract(r"(\d{4})(\d{2})")
        if not comp.empty:
            out["ano"] = pd.to_numeric(comp[0], errors="coerce")
            out["mes"] = pd.to_numeric(comp[1], errors="coerce")

    if out["uf"].isna().all():
        out["uf"] = UF

    for col in ["ano", "mes", "leitos_existentes", "leitos_sus", "uti_existente", "uti_sus"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    for col in ["municipio", "cnes"]:
        out[col] = out[col].astype(str).str.strip()

    # Remove linhas totalmente vazias de capacidade.
    out = out.dropna(how="all", subset=["leitos_existentes", "leitos_sus", "uti_existente", "uti_sus"])
    print(f"[CNES] Processado: {len(out):,} linhas")
    return out


def main() -> None:
    df_raw = coletar_cnes()
    df_final = processar_cnes(df_raw)

    destino = os.path.join(OUTPUT_PROC, "capacidade_cnes_sp.csv")
    df_final.to_csv(destino, index=False)
    print(f"\n✓ Salvo em: {destino}")
    print(df_final.head().to_string(index=False))


if __name__ == "__main__":
    main()
