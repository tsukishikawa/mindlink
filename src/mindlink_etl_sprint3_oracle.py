"""
MindLink — ETL PySUS + preparação/carga Oracle | Sprint 3
Disciplina: Building Data-Driven Applications for Data Science
Equipe She Leads — Challenge Oracle + FIAP 2026

Objetivo
--------
Executar um pipeline ETL reprodutível para o recorte experimental da MindLink:
1) extrair internações do SIH/SUS (RD) via PySUS;
2) padronizar e validar os registros;
3) identificar demência por CID-10 F00, F01, F02, F03 e G30 em diagnóstico
   principal e secundário;
4) gerar os datasets agregados no mesmo grão das tabelas de staging Oracle;
5) opcionalmente carregar STG_MINDLINK_INTERNACOES e
   STG_MINDLINK_COMORBIDADES no Oracle Autonomous Database;
6) produzir logs, arquivos de evidência e validações pós-carga.

Uso rápido
----------
Teste sem internet/PySUS:
    python mindlink_etl_sprint3_oracle.py --demo

Coleta real (exemplo):
    python mindlink_etl_sprint3_oracle.py --uf SP --anos 2024,2025 --meses 1,2,3,4,5,6,7,8,9,10,11,12 \
        --cadastro-cnes-csv data/reference/cnes_lookup.csv \
        --cid-csv data/reference/cid10.csv

Carga Oracle (credenciais por variáveis de ambiente):
    set ORACLE_USER=...
    set ORACLE_PASSWORD=...
    set ORACLE_DSN=...
    python mindlink_etl_sprint3_oracle.py --demo --oracle-load --oracle-validate

Observação
----------
O script NÃO cria ou altera o DDL do projeto. A estrutura Oracle deve existir antes da
carga. Isso mantém separadas as responsabilidades: Python faz ETL; DDL define o
modelo; DML promove staging para dimensões/fatos/views.
"""

from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# Configuração do domínio
# -----------------------------------------------------------------------------

CIDS_DEMENCIA = ("F00", "F01", "F02", "F03", "G30")

LABEL_CID_DEMENCIA = {
    "F00": "Demência na doença de Alzheimer",
    "F01": "Demência vascular",
    "F02": "Demência em outras doenças classificadas em outra parte",
    "F03": "Demência não especificada",
    "G30": "Doença de Alzheimer",
}

# Descrições mínimas usadas apenas no modo demonstrativo. Na execução real,
# --cid-csv deve apontar para o dicionário oficial do DATASUS.
LABEL_CID_DEMO = {
    "J18": "Pneumonia por microrganismo não especificado",
    "N39": "Outros transtornos do trato urinário",
    "J69": "Pneumonite devida a sólidos e líquidos",
    "S72": "Fratura do fêmur",
    "I63": "Infarto cerebral",
    "I64": "Acidente vascular cerebral não especificado",
    "E86": "Depleção de volume",
    "L89": "Úlcera de decúbito",
    "I21": "Infarto agudo do miocárdio",
    "K35": "Apendicite aguda",
    "S52": "Fratura do antebraço",
    "E11": "Diabetes mellitus tipo 2",
    "I50": "Insuficiência cardíaca",
    "K80": "Colelitíase",
}

COLUNAS_SIH = {
    "ANO_CMPT": "ano",
    "MES_CMPT": "mes",
    "MUNIC_RES": "municipio_residencia",
    "MUNIC_MOV": "codigo_ibge",
    "CNES": "cnes",
    "N_AIH": "numero_aih",
    "DIAG_PRINC": "cid_principal",
    "IDADE": "idade",
    "SEXO": "sexo",
    "DIAS_PERM": "dias_permanencia",
    "VAL_TOT": "valor_total",
    "MORTE": "obito",
    "PROC_REA": "procedimento_realizado",
    "DT_INTER": "data_internacao",
    "DT_SAIDA": "data_saida",
}

COLUNAS_STG_INTERNACOES = [
    "COMPETENCIA",
    "CODIGO_IBGE",
    "MUNICIPIO_ATENDIMENTO",
    "CNES",
    "NOME_ESTABELECIMENTO",
    "CID_PRINCIPAL",
    "DESCRICAO_CID_PRINCIPAL",
    "FAIXA_ETARIA",
    "SEXO_DESC",
    "QTD_INTERNACOES",
    "DIAS_PERMANENCIA",
    "VALOR_TOTAL",
    "QTD_OBITOS",
]

COLUNAS_STG_COMORBIDADES = [
    "COMPETENCIA",
    "CODIGO_IBGE",
    "CNES",
    "CID_PRINCIPAL",
    "CID_SECUNDARIO",
    "QTD_INTERNACOES_COM_COMORBIDADE",
    "DESCRICAO_CID_SECUNDARIO",
]

OUTPUT_RAW = Path("data/raw")
OUTPUT_PROCESSED = Path("data/processed")
OUTPUT_EVIDENCE = Path("data/evidence")


@dataclass(frozen=True)
class OracleConfig:
    user: str
    password: str
    dsn: str


# -----------------------------------------------------------------------------
# Utilitários
# -----------------------------------------------------------------------------

def configurar_logging() -> None:
    """Configura logs legíveis, úteis como evidência de execução."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def criar_pastas() -> None:
    for pasta in (OUTPUT_RAW, OUTPUT_PROCESSED, OUTPUT_EVIDENCE):
        pasta.mkdir(parents=True, exist_ok=True)


def parse_lista_inteiros(valor: str) -> list[int]:
    if not valor:
        return []
    return [int(x.strip()) for x in valor.split(",") if x.strip()]


def normalizar_codigo(valor: object, tamanho: int | None = None) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip().upper().replace(".", "")
    if texto.endswith(".0") and texto[:-2].isdigit():
        texto = texto[:-2]
    if tamanho and texto.isdigit():
        texto = texto.zfill(tamanho)
    return texto


def startswith_cid(serie: pd.Series, cids: Iterable[str] = CIDS_DEMENCIA) -> pd.Series:
    return (
        serie.fillna("")
        .astype(str)
        .str.upper()
        .str.replace(".", "", regex=False)
        .str.startswith(tuple(cids), na=False)
    )


def detectar_colunas_secundarias(df: pd.DataFrame) -> list[str]:
    """Detecta variantes comuns de colunas de diagnóstico secundário no SIH/SUS."""
    candidatas: list[str] = []
    for coluna in df.columns:
        c = coluna.upper()
        if (
            c == "DIAG_SECUN"
            or c.startswith("DIAGSEC")
            or c.startswith("DIAG_SEC")
            or c.startswith("DIAGSECUN")
        ):
            candidatas.append(coluna)
    return list(dict.fromkeys(candidatas))


# -----------------------------------------------------------------------------
# EXTRACT — SIH/SUS via PySUS
# -----------------------------------------------------------------------------

def coletar_sih_pysus(uf: str, anos: list[int], meses: list[int], grupo: str = "RD") -> pd.DataFrame:
    """Extrai registros SIH/SUS via PySUS para UF/anos/meses informados."""
    if not anos or not meses:
        raise ValueError("Informe ao menos um ano e um mês para a coleta.")

    logging.info("[EXTRACT] Iniciando SIH/SUS via PySUS")
    logging.info("[EXTRACT] UF=%s | anos=%s | meses=%s | grupo=%s", uf, anos, meses, grupo)

    try:
        from pysus import sih  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "PySUS não instalado. Execute: pip install --upgrade pysus"
        ) from exc

    try:
        df = sih(
            state=uf,
            year=anos,
            month=meses,
            group=grupo,
            as_dataframe=True,
            show_progress=True,
        )
    except TypeError:
        # Compatibilidade com versões que não expõem show_progress.
        df = sih(
            state=uf,
            year=anos,
            month=meses,
            group=grupo,
            as_dataframe=True,
        )
    except Exception as exc:
        logging.exception("[EXTRACT] Falha na coleta SIH/SUS")
        raise RuntimeError(f"Falha ao coletar SIH/SUS: {exc}") from exc

    if df is None or len(df) == 0:
        raise RuntimeError("PySUS retornou dataset vazio para o recorte solicitado.")

    if not isinstance(df, pd.DataFrame):
        try:
            df = pd.DataFrame(df)
        except Exception as exc:
            raise TypeError("O retorno do PySUS não pôde ser convertido para DataFrame.") from exc

    logging.info("[EXTRACT] Coleta concluída: %s linhas x %s colunas", f"{len(df):,}", len(df.columns))
    return df


def gerar_base_demo(n: int = 3000) -> pd.DataFrame:
    """Base sintética determinística para testar todo o pipeline sem internet."""
    logging.warning("[DEMO] Base sintética: usar apenas para teste do código, nunca como resultado real.")
    rng = np.random.default_rng(42)

    estabelecimentos = pd.DataFrame(
        [
            ("355030", "SAO PAULO", "2077574", "CONJUNTO HOSPITALAR DO MANDAQUI SAO PAULO"),
            ("354990", "SAO JOSE DOS CAMPOS", "0009628", "HOSPITAL MUNICIPAL DR JOSE DE CARVALHO FLORENCE"),
            ("350950", "CAMPINAS", "2079798", "HOSPITAL MUNICIPAL DE CAMPINAS"),
            ("352710", "LINS", "2081725", "SANTA CASA REGIONAL"),
        ],
        columns=["MUNIC_MOV", "MUNICIPIO_ATENDIMENTO", "CNES", "NOME_ESTABELECIMENTO"],
    )

    idx_estab = rng.integers(0, len(estabelecimentos), n)
    cadastro = estabelecimentos.iloc[idx_estab].reset_index(drop=True)

    tem_demencia = rng.random(n) < 0.18
    demencia_principal = tem_demencia & (rng.random(n) < 0.30)
    demencia_secundaria = tem_demencia & ~demencia_principal

    causas = np.array(["J18", "N39", "J69", "S72", "I63", "I64", "E86", "L89"])
    outros = np.array(["I21", "K35", "S52", "J18", "N39", "E11", "I50", "K80"])

    diag_princ = np.empty(n, dtype=object)
    diag_princ[demencia_principal] = rng.choice(CIDS_DEMENCIA, demencia_principal.sum())
    diag_princ[demencia_secundaria] = rng.choice(causas, demencia_secundaria.sum())
    diag_princ[~tem_demencia] = rng.choice(outros, (~tem_demencia).sum())

    diag_secun = np.full(n, "", dtype=object)
    diag_secun[demencia_secundaria] = rng.choice(CIDS_DEMENCIA, demencia_secundaria.sum())
    mascara_comorbidade_extra = tem_demencia & (rng.random(n) < 0.50)
    diagsec2 = np.full(n, "", dtype=object)
    diagsec2[mascara_comorbidade_extra] = rng.choice(causas, mascara_comorbidade_extra.sum())

    idade = np.where(
        tem_demencia,
        rng.normal(79, 9, n).clip(45, 105).astype(int),
        rng.normal(52, 21, n).clip(0, 105).astype(int),
    )
    dias = np.where(
        tem_demencia,
        rng.gamma(3.0, 3.5, n).astype(int),
        rng.gamma(2.0, 2.5, n).astype(int),
    )
    dias = np.maximum(dias, 0)
    valor = np.round(np.maximum(dias, 1) * rng.normal(350, 80, n).clip(120, 900), 2)

    df = pd.DataFrame(
        {
            "ANO_CMPT": rng.choice([2024, 2025], n),
            "MES_CMPT": rng.choice(range(1, 13), n),
            "MUNIC_RES": cadastro["MUNIC_MOV"],
            "MUNIC_MOV": cadastro["MUNIC_MOV"],
            "MUNICIPIO_ATENDIMENTO": cadastro["MUNICIPIO_ATENDIMENTO"],
            "CNES": cadastro["CNES"],
            "NOME_ESTABELECIMENTO": cadastro["NOME_ESTABELECIMENTO"],
            "N_AIH": [f"{x:012d}" for x in rng.integers(1, 999_999_999, n)],
            "DIAG_PRINC": diag_princ,
            "DIAG_SECUN": diag_secun,
            "DIAGSEC2": diagsec2,
            "IDADE": idade,
            "SEXO": rng.choice([1, 3], n),
            "DIAS_PERM": dias,
            "VAL_TOT": valor,
            "MORTE": (rng.random(n) < np.where(tem_demencia, 0.12, 0.03)).astype(int),
            "PROC_REA": rng.choice(["0303010037", "0303060069", "0408050626"], n),
        }
    )
    logging.info("[DEMO] Dataset gerado: %s linhas", f"{len(df):,}")
    return df


# -----------------------------------------------------------------------------
# TRANSFORM — padronização, CID, qualidade e enriquecimento
# -----------------------------------------------------------------------------

def normalizar_colunas(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    secundarias_originais = detectar_colunas_secundarias(df)

    renomear = {orig: novo for orig, novo in COLUNAS_SIH.items() if orig in df.columns}
    df = df.rename(columns=renomear)

    secundarias_normalizadas: list[str] = []
    for i, col_original in enumerate(secundarias_originais, start=1):
        col_atual = "diag_secundario" if col_original == "DIAG_SECUN" else col_original
        if col_original == "DIAG_SECUN" and col_original in df.columns:
            df = df.rename(columns={col_original: "diag_secundario"})
        if col_atual in df.columns:
            secundarias_normalizadas.append(col_atual)

    # Remove duplicidade de nomes preservando ordem.
    secundarias_normalizadas = list(dict.fromkeys(secundarias_normalizadas))
    df.attrs["colunas_secundarias"] = secundarias_normalizadas

    logging.info(
        "[TRANSFORM] Diagnósticos secundários detectados (%d): %s",
        len(secundarias_normalizadas),
        secundarias_normalizadas or "nenhum",
    )
    return df


def padronizar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ("ano", "mes", "idade", "dias_permanencia", "valor_total", "obito"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ("codigo_ibge", "cnes", "numero_aih", "cid_principal"):
        if col in df.columns:
            tamanho = 6 if col == "codigo_ibge" else 7 if col == "cnes" else None
            df[col] = df[col].map(lambda x: normalizar_codigo(x, tamanho))

    secundarias = df.attrs.get("colunas_secundarias", [])
    for col in secundarias:
        if col in df.columns:
            df[col] = df[col].map(normalizar_codigo)

    if "sexo" in df.columns:
        df["sexo_desc"] = (
            df["sexo"].astype("Int64").astype(str).map({"1": "MASCULINO", "3": "FEMININO"}).fillna("IGNORADO")
        )

    if "idade" in df.columns:
        condicoes = [
            df["idade"].between(0, 59, inclusive="both"),
            df["idade"].between(60, 69, inclusive="both"),
            df["idade"].between(70, 79, inclusive="both"),
            df["idade"].between(80, 89, inclusive="both"),
            df["idade"] >= 90,
        ]
        df["faixa_etaria"] = np.select(
            condicoes,
            ["ATE_59", "60_69", "70_79", "80_89", "90_MAIS"],
            default="NAO_INFORMADA",
        )

    if "ano" in df.columns and "mes" in df.columns:
        df["competencia"] = (
            df["ano"].astype("Int64") * 100 + df["mes"].astype("Int64")
        ).astype("Int64")

    return df


def criar_flags_demencia(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "cid_principal" not in df.columns:
        raise ValueError("Coluna DIAG_PRINC/cid_principal não encontrada.")

    secundarias = [c for c in df.attrs.get("colunas_secundarias", []) if c in df.columns]
    mask_principal = startswith_cid(df["cid_principal"])

    if secundarias:
        masks = [startswith_cid(df[c]) for c in secundarias]
        mask_secundario = pd.Series(np.logical_or.reduce(masks), index=df.index)
    else:
        mask_secundario = pd.Series(False, index=df.index)

    df["demencia_diag_principal"] = mask_principal.astype("int8")
    df["demencia_diag_secundario"] = mask_secundario.astype("int8")
    df["tem_demencia"] = (mask_principal | mask_secundario).astype("int8")

    df["demencia_em"] = np.select(
        [
            mask_principal & mask_secundario,
            mask_principal & ~mask_secundario,
            ~mask_principal & mask_secundario,
        ],
        ["principal_e_secundaria", "principal", "secundaria"],
        default="nao_detectada",
    )
    return df


def carregar_lookup_cnes(caminho: str | None) -> pd.DataFrame | None:
    if not caminho:
        return None
    lookup = pd.read_csv(caminho, dtype=str)
    lookup.columns = [c.upper().strip() for c in lookup.columns]
    obrigatorias = {"CODIGO_IBGE", "MUNICIPIO_ATENDIMENTO", "CNES", "NOME_ESTABELECIMENTO"}
    faltantes = obrigatorias - set(lookup.columns)
    if faltantes:
        raise ValueError(f"Lookup CNES sem colunas obrigatórias: {sorted(faltantes)}")
    lookup = lookup[list(obrigatorias)].copy()
    lookup["CODIGO_IBGE"] = lookup["CODIGO_IBGE"].map(lambda x: normalizar_codigo(x, 6))
    lookup["CNES"] = lookup["CNES"].map(lambda x: normalizar_codigo(x, 7))
    return lookup.drop_duplicates(subset=["CODIGO_IBGE", "CNES"])


def carregar_lookup_cid(caminho: str | None) -> dict[str, str]:
    """Carrega dicionário CID flexível; procura automaticamente colunas de código/descrição."""
    if not caminho:
        return {}
    cid = pd.read_csv(caminho, dtype=str, sep=None, engine="python")
    mapa_colunas = {c.upper().strip(): c for c in cid.columns}

    candidatos_codigo = ["CODIGO_CID", "CID", "CODIGO", "CD_CID", "CID10"]
    candidatos_desc = ["DESCRICAO_CID", "DESCRICAO", "DESCR", "DS_CID", "NOME"]

    col_codigo = next((mapa_colunas[x] for x in candidatos_codigo if x in mapa_colunas), None)
    col_desc = next((mapa_colunas[x] for x in candidatos_desc if x in mapa_colunas), None)
    if not col_codigo or not col_desc:
        raise ValueError("CSV CID precisa conter uma coluna de código e uma de descrição.")

    cid = cid[[col_codigo, col_desc]].dropna().copy()
    cid[col_codigo] = cid[col_codigo].map(normalizar_codigo)
    return dict(zip(cid[col_codigo], cid[col_desc].astype(str).str.strip()))


def enriquecer_cnes(df: pd.DataFrame, lookup_cnes: pd.DataFrame | None) -> pd.DataFrame:
    df = df.copy()

    # Modo demo ou fonte já enriquecida.
    if {"MUNICIPIO_ATENDIMENTO", "NOME_ESTABELECIMENTO"}.issubset(df.columns):
        df["municipio_atendimento"] = df["MUNICIPIO_ATENDIMENTO"].astype(str).str.strip().str.upper()
        df["nome_estabelecimento"] = df["NOME_ESTABELECIMENTO"].astype(str).str.strip().str.upper()
        return df

    if lookup_cnes is None:
        raise ValueError(
            "A staging Oracle exige MUNICIPIO_ATENDIMENTO e NOME_ESTABELECIMENTO. "
            "Informe --cadastro-cnes-csv para enriquecer a coleta real."
        )

    lookup = lookup_cnes.rename(
        columns={
            "CODIGO_IBGE": "codigo_ibge",
            "CNES": "cnes",
            "MUNICIPIO_ATENDIMENTO": "municipio_atendimento",
            "NOME_ESTABELECIMENTO": "nome_estabelecimento",
        }
    )
    df = df.merge(lookup, on=["codigo_ibge", "cnes"], how="left", validate="m:1")
    return df


def descricao_cid(codigo: str, lookup_cid: dict[str, str]) -> str:
    codigo = normalizar_codigo(codigo)
    if codigo in lookup_cid:
        return lookup_cid[codigo]
    prefixo = codigo[:3]
    if prefixo in LABEL_CID_DEMENCIA:
        return LABEL_CID_DEMENCIA[prefixo]
    if prefixo in LABEL_CID_DEMO:
        return LABEL_CID_DEMO[prefixo]
    return f"CID {codigo} - descrição não carregada"


def validar_dados(df: pd.DataFrame) -> dict[str, int]:
    """Executa verificações de qualidade antes de qualquer agregação/carga."""
    obrigatorias = [
        "ano", "mes", "codigo_ibge", "cnes", "numero_aih", "cid_principal",
        "idade", "dias_permanencia", "valor_total", "obito", "competencia",
    ]
    faltantes = [c for c in obrigatorias if c not in df.columns]
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes após transformação: {faltantes}")

    erros = {
        "mes_invalido": int((~df["mes"].between(1, 12, inclusive="both")).fillna(True).sum()),
        "idade_negativa": int((df["idade"] < 0).fillna(False).sum()),
        "permanencia_negativa": int((df["dias_permanencia"] < 0).fillna(False).sum()),
        "valor_negativo": int((df["valor_total"] < 0).fillna(False).sum()),
        "aih_duplicada": int(df["numero_aih"].duplicated(keep=False).sum()),
        "ibge_vazio": int((df["codigo_ibge"].astype(str).str.len() == 0).sum()),
        "cnes_vazio": int((df["cnes"].astype(str).str.len() == 0).sum()),
        "cid_principal_vazio": int((df["cid_principal"].astype(str).str.len() == 0).sum()),
    }

    criticos = ["mes_invalido", "idade_negativa", "permanencia_negativa", "valor_negativo", "ibge_vazio", "cnes_vazio"]
    if any(erros[k] > 0 for k in criticos):
        raise ValueError(f"Falha nas regras críticas de qualidade: {erros}")

    logging.info("[QUALITY] Validação concluída: %s", erros)
    return erros


def transformar(df_raw: pd.DataFrame, lookup_cnes: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = normalizar_colunas(df_raw)
    attrs = dict(df.attrs)
    df = padronizar_tipos(df)
    df.attrs.update(attrs)
    df = criar_flags_demencia(df)
    df = enriquecer_cnes(df, lookup_cnes)
    validar_dados(df)

    df_demencia = df[df["tem_demencia"] == 1].copy()
    logging.info(
        "[TRANSFORM] Registros relacionados à demência: %s de %s (%.2f%%)",
        f"{len(df_demencia):,}", f"{len(df):,}", 100 * len(df_demencia) / len(df) if len(df) else 0,
    )
    return df, df_demencia


# -----------------------------------------------------------------------------
# LOAD PREP — datasets no grão exato do DDL Oracle
# -----------------------------------------------------------------------------

def construir_stg_internacoes(df_demencia: pd.DataFrame, lookup_cid: dict[str, str]) -> pd.DataFrame:
    df = df_demencia.copy()
    df["descricao_cid_principal"] = df["cid_principal"].map(lambda x: descricao_cid(x, lookup_cid))

    chaves = [
        "competencia", "codigo_ibge", "municipio_atendimento", "cnes",
        "nome_estabelecimento", "cid_principal", "descricao_cid_principal",
        "faixa_etaria", "sexo_desc",
    ]
    faltantes = [c for c in chaves if c not in df.columns]
    if faltantes:
        raise ValueError(f"Campos ausentes para STG_MINDLINK_INTERNACOES: {faltantes}")

    stg = (
        df.groupby(chaves, dropna=False, as_index=False)
        .agg(
            QTD_INTERNACOES=("numero_aih", "count"),
            DIAS_PERMANENCIA=("dias_permanencia", "sum"),
            VALOR_TOTAL=("valor_total", "sum"),
            QTD_OBITOS=("obito", "sum"),
        )
        .rename(
            columns={
                "competencia": "COMPETENCIA",
                "codigo_ibge": "CODIGO_IBGE",
                "municipio_atendimento": "MUNICIPIO_ATENDIMENTO",
                "cnes": "CNES",
                "nome_estabelecimento": "NOME_ESTABELECIMENTO",
                "cid_principal": "CID_PRINCIPAL",
                "descricao_cid_principal": "DESCRICAO_CID_PRINCIPAL",
                "faixa_etaria": "FAIXA_ETARIA",
                "sexo_desc": "SEXO_DESC",
            }
        )
    )
    stg["COMPETENCIA"] = stg["COMPETENCIA"].astype(int)
    stg["QTD_INTERNACOES"] = stg["QTD_INTERNACOES"].astype(int)
    stg["DIAS_PERMANENCIA"] = stg["DIAS_PERMANENCIA"].fillna(0).round().astype(int)
    stg["VALOR_TOTAL"] = stg["VALOR_TOTAL"].fillna(0).round(2)
    stg["QTD_OBITOS"] = stg["QTD_OBITOS"].fillna(0).round().astype(int)
    return stg[COLUNAS_STG_INTERNACOES]


def construir_stg_comorbidades(df_demencia: pd.DataFrame, lookup_cid: dict[str, str]) -> pd.DataFrame:
    secundarias = [c for c in df_demencia.attrs.get("colunas_secundarias", []) if c in df_demencia.columns]
    if not secundarias:
        return pd.DataFrame(columns=COLUNAS_STG_COMORBIDADES)

    partes: list[pd.DataFrame] = []
    for coluna in secundarias:
        parte = df_demencia[["competencia", "codigo_ibge", "cnes", "cid_principal", coluna]].copy()
        parte = parte.rename(columns={coluna: "cid_secundario"})
        parte["cid_secundario"] = parte["cid_secundario"].map(normalizar_codigo)
        parte = parte[parte["cid_secundario"].str.len() > 0]
        partes.append(parte)

    if not partes:
        return pd.DataFrame(columns=COLUNAS_STG_COMORBIDADES)

    longo = pd.concat(partes, ignore_index=True).drop_duplicates()
    longo["descricao_cid_secundario"] = longo["cid_secundario"].map(lambda x: descricao_cid(x, lookup_cid))

    stg = (
        longo.groupby(
            ["competencia", "codigo_ibge", "cnes", "cid_principal", "cid_secundario", "descricao_cid_secundario"],
            dropna=False,
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "competencia": "COMPETENCIA",
                "codigo_ibge": "CODIGO_IBGE",
                "cnes": "CNES",
                "cid_principal": "CID_PRINCIPAL",
                "cid_secundario": "CID_SECUNDARIO",
                "size": "QTD_INTERNACOES_COM_COMORBIDADE",
                "descricao_cid_secundario": "DESCRICAO_CID_SECUNDARIO",
            }
        )
    )
    stg["COMPETENCIA"] = stg["COMPETENCIA"].astype(int)
    stg["QTD_INTERNACOES_COM_COMORBIDADE"] = stg["QTD_INTERNACOES_COM_COMORBIDADE"].astype(int)
    return stg[COLUNAS_STG_COMORBIDADES]


def validar_staging(stg_int: pd.DataFrame, stg_com: pd.DataFrame) -> None:
    if stg_int.empty:
        raise ValueError("STG_MINDLINK_INTERNACOES resultou vazia.")

    nulos_int = stg_int[COLUNAS_STG_INTERNACOES].isna().sum().sum()
    if int(nulos_int) > 0:
        raise ValueError(f"STG_MINDLINK_INTERNACOES possui {int(nulos_int)} valores nulos.")

    grao_int = ["COMPETENCIA", "CNES", "CID_PRINCIPAL", "FAIXA_ETARIA", "SEXO_DESC"]
    duplic_int = int(stg_int.duplicated(grao_int, keep=False).sum())
    if duplic_int:
        raise ValueError(f"Staging de internações viola o grão esperado em {duplic_int} linhas.")

    if not stg_com.empty:
        nulos_com = stg_com[COLUNAS_STG_COMORBIDADES].isna().sum().sum()
        if int(nulos_com) > 0:
            raise ValueError(f"STG_MINDLINK_COMORBIDADES possui {int(nulos_com)} valores nulos.")

    logging.info(
        "[QUALITY] Staging válida: internações=%s | comorbidades=%s",
        f"{len(stg_int):,}", f"{len(stg_com):,}",
    )


# -----------------------------------------------------------------------------
# Persistência local e evidências
# -----------------------------------------------------------------------------

def gerar_resumo(df_tratado: pd.DataFrame, df_demencia: pd.DataFrame) -> pd.DataFrame:
    principal = int(df_tratado["demencia_diag_principal"].sum())
    secundaria = int(df_tratado["demencia_diag_secundario"].sum())
    qualquer = int(df_tratado["tem_demencia"].sum())
    perda = max(qualquer - principal, 0)

    return pd.DataFrame(
        [
            ("Total de AIHs analisadas", len(df_tratado)),
            ("Demência no diagnóstico principal", principal),
            ("Demência em diagnóstico secundário", secundaria),
            ("Demência em qualquer diagnóstico considerado", qualquer),
            ("Casos adicionais vs. filtro apenas principal", perda),
            ("Linhas tratadas relacionadas à demência", len(df_demencia)),
        ],
        columns=["INDICADOR", "VALOR"],
    )


def salvar_saidas(
    df_raw: pd.DataFrame,
    df_tratado: pd.DataFrame,
    df_demencia: pd.DataFrame,
    stg_int: pd.DataFrame,
    stg_com: pd.DataFrame,
) -> None:
    # Amostra do bruto: o nome explicita que não é a base integral.
    df_raw.head(5000).to_csv(OUTPUT_RAW / "mindlink_sih_raw_amostra.csv", index=False)
    df_demencia.to_csv(OUTPUT_PROCESSED / "mindlink_internacoes_demencia_tratado.csv", index=False)
    stg_int.to_csv(OUTPUT_PROCESSED / "stg_mindlink_internacoes_python.csv", index=False)
    stg_com.to_csv(OUTPUT_PROCESSED / "stg_mindlink_comorbidades_python.csv", index=False)

    resumo = gerar_resumo(df_tratado, df_demencia)
    resumo.to_csv(OUTPUT_EVIDENCE / "mindlink_resumo_etl.csv", index=False)

    try:
        df_demencia.to_parquet(OUTPUT_PROCESSED / "mindlink_internacoes_demencia_tratado.parquet", index=False)
    except Exception as exc:
        logging.warning("[LOAD] Parquet não gerado; CSV permanece disponível. Motivo: %s", exc)

    logging.info("[LOAD] Arquivos locais gravados em data/processed e data/evidence")


def exibir_evidencias(
    df_tratado: pd.DataFrame,
    df_demencia: pd.DataFrame,
    stg_int: pd.DataFrame,
    stg_com: pd.DataFrame,
) -> None:
    resumo = gerar_resumo(df_tratado, df_demencia)
    print("\n" + "=" * 78)
    print("MINDLINK — EVIDÊNCIA DE EXECUÇÃO DO ETL PYTHON / SPRINT 3")
    print("=" * 78)
    print("\n[1] Resumo da transformação")
    print(resumo.to_string(index=False))
    print("\n[2] Dataset no grão do DDL Oracle")
    print(f"STG_MINDLINK_INTERNACOES: {len(stg_int):,} linhas")
    print(f"STG_MINDLINK_COMORBIDADES: {len(stg_com):,} linhas")
    print("\n[3] Competências encontradas")
    print(", ".join(str(x) for x in sorted(stg_int["COMPETENCIA"].unique())))
    print("\n[4] Preview STG_MINDLINK_INTERNACOES")
    print(stg_int.head(8).to_string(index=False))
    print("\n[5] Validação")
    print("✓ Transformação concluída")
    print("✓ Regras críticas de qualidade aprovadas")
    print("✓ Grão compatível com o DDL da Sprint 3")


# -----------------------------------------------------------------------------
# Oracle — carga opcional e validação pós-carga
# -----------------------------------------------------------------------------

def obter_oracle_config() -> OracleConfig:
    user = os.getenv("ORACLE_USER", "").strip()
    password = os.getenv("ORACLE_PASSWORD", "").strip()
    dsn = os.getenv("ORACLE_DSN", "").strip()
    if not all((user, password, dsn)):
        raise ValueError("Defina ORACLE_USER, ORACLE_PASSWORD e ORACLE_DSN para usar o Oracle.")
    return OracleConfig(user=user, password=password, dsn=dsn)


def _python_scalar(valor: object) -> object:
    if pd.isna(valor):
        return None
    if isinstance(valor, np.generic):
        return valor.item()
    return valor


def _rows(df: pd.DataFrame, cols: Sequence[str]) -> list[tuple[object, ...]]:
    return [tuple(_python_scalar(v) for v in linha) for linha in df[list(cols)].itertuples(index=False, name=None)]


def conectar_oracle(config: OracleConfig):
    try:
        import oracledb  # type: ignore
    except ImportError as exc:
        raise ImportError("Instale o driver Oracle com: pip install oracledb") from exc
    return oracledb.connect(user=config.user, password=config.password, dsn=config.dsn)


def carregar_oracle(stg_int: pd.DataFrame, stg_com: pd.DataFrame, replace_competencias: bool = True) -> None:
    """Carrega as duas stagings já existentes no DDL. Não cria objetos de banco."""
    config = obter_oracle_config()
    competencias = sorted(set(stg_int["COMPETENCIA"].astype(int).tolist()))

    sql_int = """
        INSERT INTO STG_MINDLINK_INTERNACOES
        (COMPETENCIA, CODIGO_IBGE, MUNICIPIO_ATENDIMENTO, CNES,
         NOME_ESTABELECIMENTO, CID_PRINCIPAL, DESCRICAO_CID_PRINCIPAL,
         FAIXA_ETARIA, SEXO_DESC, QTD_INTERNACOES, DIAS_PERMANENCIA,
         VALOR_TOTAL, QTD_OBITOS)
        VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13)
    """
    sql_com = """
        INSERT INTO STG_MINDLINK_COMORBIDADES
        (COMPETENCIA, CODIGO_IBGE, CNES, CID_PRINCIPAL, CID_SECUNDARIO,
         QTD_INTERNACOES_COM_COMORBIDADE, DESCRICAO_CID_SECUNDARIO)
        VALUES (:1,:2,:3,:4,:5,:6,:7)
    """

    with conectar_oracle(config) as conn:
        with conn.cursor() as cur:
            if replace_competencias:
                for competencia in competencias:
                    cur.execute("DELETE FROM STG_MINDLINK_INTERNACOES WHERE COMPETENCIA = :1", [competencia])
                    cur.execute("DELETE FROM STG_MINDLINK_COMORBIDADES WHERE COMPETENCIA = :1", [competencia])
                logging.info("[ORACLE] Competências existentes removidas antes da recarga: %s", competencias)

            cur.executemany(sql_int, _rows(stg_int, COLUNAS_STG_INTERNACOES), batcherrors=True)
            erros = cur.getbatcherrors()
            if erros:
                raise RuntimeError(f"Erros na carga STG_MINDLINK_INTERNACOES: {erros[:5]}")

            if not stg_com.empty:
                cur.executemany(sql_com, _rows(stg_com, COLUNAS_STG_COMORBIDADES), batcherrors=True)
                erros = cur.getbatcherrors()
                if erros:
                    raise RuntimeError(f"Erros na carga STG_MINDLINK_COMORBIDADES: {erros[:5]}")

        conn.commit()
        logging.info("[ORACLE] Carga confirmada com COMMIT")


def validar_oracle() -> pd.DataFrame:
    config = obter_oracle_config()
    objetos = [
        "STG_MINDLINK_INTERNACOES",
        "STG_MINDLINK_COMORBIDADES",
        "STG_MINDLINK_CAPACIDADE",
        "FATO_INTERNACAO_MENSAL",
        "FATO_COMORBIDADE_MENSAL",
        "FATO_CAPACIDADE_MENSAL",
        "VW_PRESSAO_HOSPITALAR",
        "VW_CANDIDATOS_REALOCACAO",
    ]

    resultados: list[tuple[str, int | str]] = []
    with conectar_oracle(config) as conn:
        with conn.cursor() as cur:
            for objeto in objetos:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {objeto}")
                    qtd = int(cur.fetchone()[0])
                    resultados.append((objeto, qtd))
                except Exception as exc:
                    resultados.append((objeto, f"ERRO: {exc}"))

    df = pd.DataFrame(resultados, columns=["OBJETO_ORACLE", "LINHAS"])
    print("\n[6] Validação pós-carga no Oracle")
    print(df.to_string(index=False))
    df.to_csv(OUTPUT_EVIDENCE / "oracle_contagens_pos_carga.csv", index=False)
    return df


# -----------------------------------------------------------------------------
# Programa principal
# -----------------------------------------------------------------------------

def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MindLink ETL PySUS + Oracle — Sprint 3")
    parser.add_argument("--uf", default=os.getenv("MINDLINK_UF", "SP"))
    parser.add_argument("--anos", default=os.getenv("MINDLINK_ANOS", "2024,2025"))
    parser.add_argument("--meses", default=os.getenv("MINDLINK_MESES", "1,2,3,4,5,6,7,8,9,10,11,12"))
    parser.add_argument("--grupo", default=os.getenv("MINDLINK_GRUPO", "RD"))
    parser.add_argument("--demo", action="store_true", help="Executa pipeline completo com dados sintéticos.")
    parser.add_argument("--demo-linhas", type=int, default=3000)
    parser.add_argument("--cadastro-cnes-csv", default=None, help="Lookup com CODIGO_IBGE, MUNICIPIO_ATENDIMENTO, CNES e NOME_ESTABELECIMENTO.")
    parser.add_argument("--cid-csv", default=None, help="Dicionário CID oficial (código + descrição).")
    parser.add_argument("--oracle-load", action="store_true", help="Carrega as stagings existentes no Oracle.")
    parser.add_argument("--oracle-validate", action="store_true", help="Consulta contagens dos objetos Oracle após o ETL.")
    parser.add_argument("--append-staging", action="store_true", help="Não remove competências existentes antes da carga (não recomendado).")
    return parser


def main() -> None:
    configurar_logging()
    criar_pastas()
    args = criar_parser().parse_args()

    anos = parse_lista_inteiros(args.anos)
    meses = parse_lista_inteiros(args.meses)
    lookup_cnes = carregar_lookup_cnes(args.cadastro_cnes_csv)
    lookup_cid = carregar_lookup_cid(args.cid_csv)

    if args.demo:
        df_raw = gerar_base_demo(args.demo_linhas)
    else:
        df_raw = coletar_sih_pysus(args.uf, anos, meses, args.grupo)

    df_tratado, df_demencia = transformar(df_raw, lookup_cnes)
    stg_int = construir_stg_internacoes(df_demencia, lookup_cid)
    stg_com = construir_stg_comorbidades(df_demencia, lookup_cid)
    validar_staging(stg_int, stg_com)

    salvar_saidas(df_raw, df_tratado, df_demencia, stg_int, stg_com)
    exibir_evidencias(df_tratado, df_demencia, stg_int, stg_com)

    if args.oracle_load:
        carregar_oracle(stg_int, stg_com, replace_competencias=not args.append_staging)

    if args.oracle_validate:
        validar_oracle()

    print("\n✓ MindLink ETL concluído com sucesso.")


if __name__ == "__main__":
    main()
