"""
╔════════════════════════════════════════════════════════════╗
║  MindLink — Modelo Analítico-Preditivo da Sprint 3          ║
║  Usa saída real do PySUS e explicita premissas de projeção   ║
╚════════════════════════════════════════════════════════════╝

Entradas esperadas:
    data/processed/mindlink_internacoes_sp.parquet
    data/processed/comparativo_filtro_demencia.csv

Saídas geradas:
    data/processed/historico_indicadores.csv
    data/processed/comorbidades.csv
    data/processed/territorio_scores.csv
    data/processed/projecao_demencia_2050.csv

Ponto metodológico:
    A projeção nacional ainda usa uma premissa simplificada de taxa por 100 mil
    habitantes 60+. A Sprint 3 deve documentar isso como premissa auditável, não
    como certeza causal. A melhoria principal aqui é que histórico, comorbidades
    e ranking territorial passam a nascer da base PySUS tratada.
"""

from __future__ import annotations

import os
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

warnings.filterwarnings("ignore")

OUTPUT_PROC = "data/processed/"
os.makedirs(OUTPUT_PROC, exist_ok=True)

ARQUIVO_INTERNACOES = os.path.join(OUTPUT_PROC, "mindlink_internacoes_sp.parquet")
ARQUIVO_COMPAT = os.path.join(OUTPUT_PROC, "mindlink_demencia_sp.parquet")
ARQUIVO_COMPARATIVO = os.path.join(OUTPUT_PROC, "comparativo_filtro_demencia.csv")

# Premissa herdada do deck/protótipo. Idealmente será recalculada com população 60+ do recorte.
TAXA_OBSERVADA_FALLBACK = 24.25  # AIH por 100 mil habitantes 60+
ANO_BASE = 2025
ANO_FIM = 2050
VALOR_MEDIO_BASE = 4000.0

POP_60_BRASIL = {
    2020: 29.9,
    2025: 34.6,
    2030: 40.3,
    2035: 47.1,
    2040: 53.7,
    2045: 59.1,
    2050: 64.5,
}

CENARIOS_SIGTAP = {
    "A_congelado": 0.000,
    "B_parcial": 0.0175,
    "C_pleno": 0.035,
}

DESCRICAO_CID_ASSOCIADO = {
    "J18": "Pneumonia",
    "J69": "Pneumonite aspirativa",
    "N39": "Infecção urinária",
    "S72": "Fratura de fêmur",
    "I63": "AVC isquêmico",
    "I64": "AVC não especificado",
    "E86": "Desidratação",
    "L89": "Úlcera de pressão",
    "I50": "Insuficiência cardíaca",
}


def _ler_internacoes() -> pd.DataFrame:
    caminho = ARQUIVO_INTERNACOES if os.path.exists(ARQUIVO_INTERNACOES) else ARQUIVO_COMPAT
    if not os.path.exists(caminho):
        raise FileNotFoundError(
            "Base PySUS tratada não encontrada. Rode primeiro: python 01_coleta_pysus.py"
        )
    df = pd.read_parquet(caminho)
    print(f"[Entrada] {caminho} · {len(df):,} linhas")
    return df


def construir_historico(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega indicadores anuais reais a partir da base PySUS tratada."""
    df = df.copy()
    df["ano"] = pd.to_numeric(df.get("ano"), errors="coerce")
    df = df.dropna(subset=["ano"])
    df["ano"] = df["ano"].astype(int)

    for col in ["valor_total", "dias_permanencia", "obito", "demencia_principal", "demencia_secundaria"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    hist = df.groupby("ano").agg(
        internacoes=("ano", "size"),
        internacoes_principal=("demencia_principal", "sum") if "demencia_principal" in df.columns else ("ano", "size"),
        internacoes_secundaria=("demencia_secundaria", "sum") if "demencia_secundaria" in df.columns else ("ano", "size"),
        valor_medio=("valor_total", "mean") if "valor_total" in df.columns else ("ano", "size"),
        perm_media=("dias_permanencia", "mean") if "dias_permanencia" in df.columns else ("ano", "size"),
        obitos=("obito", "sum") if "obito" in df.columns else ("ano", "size"),
    ).reset_index()

    hist["valor_medio"] = hist["valor_medio"].round(2)
    hist["perm_media"] = hist["perm_media"].round(2)
    hist["letalidade_pct"] = (hist["obitos"] / hist["internacoes"] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    return hist


def gerar_comorbidades_reais(df: pd.DataFrame) -> pd.DataFrame:
    """Causas principais quando a demência foi detectada como secundária.

    Isso substitui o DataFrame manual/simulado do protótipo e vira uma evidência
    forte da tese: a demência aparece como comorbidade por trás de pneumonia,
    infecção urinária, fratura de fêmur etc.
    """
    if "demencia_em" not in df.columns or "cid_principal" not in df.columns:
        return pd.DataFrame(columns=["cid_secundario", "descricao", "internacoes"])

    sec = df[df["demencia_em"].astype(str).str.contains("secundaria", na=False)].copy()
    if sec.empty:
        return pd.DataFrame(columns=["cid_secundario", "descricao", "internacoes"])

    sec["cid_secundario"] = sec["cid_principal"].astype(str).str[:3].str.upper()
    out = sec.groupby("cid_secundario").size().reset_index(name="internacoes")
    out["descricao"] = out["cid_secundario"].map(DESCRICAO_CID_ASSOCIADO).fillna("Outra causa principal associada")
    out = out.sort_values("internacoes", ascending=False)
    return out[["cid_secundario", "descricao", "internacoes"]]


def gerar_ranking_territorial(df: pd.DataFrame) -> pd.DataFrame:
    """Gera ranking territorial real a partir da base PySUS tratada.

    Nesta versão, o território é o município de residência codificado no SIH.
    O score combina volume, permanência, custo e óbitos em escala 0–100.
    Quando CNES/leitos entrar, o score pode incorporar internações por leito SUS.
    """
    if "municipio_residencia" not in df.columns:
        return pd.DataFrame(columns=["uf", "nome", "crescimento_pct", "score", "nivel"])

    base = df.copy()
    base["municipio_residencia"] = base["municipio_residencia"].astype(str).str[:6]
    for col in ["valor_total", "dias_permanencia", "obito"]:
        if col in base.columns:
            base[col] = pd.to_numeric(base[col], errors="coerce").fillna(0)

    terr = base.groupby("municipio_residencia").agg(
        internacoes=("municipio_residencia", "size"),
        perm_media=("dias_permanencia", "mean") if "dias_permanencia" in base.columns else ("municipio_residencia", "size"),
        valor_total=("valor_total", "sum") if "valor_total" in base.columns else ("municipio_residencia", "size"),
        obitos=("obito", "sum") if "obito" in base.columns else ("municipio_residencia", "size"),
    ).reset_index()

    def norm(s: pd.Series) -> pd.Series:
        s = pd.to_numeric(s, errors="coerce").fillna(0)
        if s.max() == s.min():
            return pd.Series(50, index=s.index)
        return (s - s.min()) / (s.max() - s.min()) * 100

    terr["score"] = (
        norm(terr["internacoes"]) * 0.45
        + norm(terr["perm_media"]) * 0.20
        + norm(terr["valor_total"]) * 0.20
        + norm(terr["obitos"]) * 0.15
    ).round().astype(int)

    terr["nivel"] = pd.cut(
        terr["score"],
        bins=[-1, 39, 59, 74, 84, 100],
        labels=["Baixo", "Médio", "Médio-Alto", "Alto", "Crítico"],
    ).astype(str)
    terr["uf"] = "SP"
    terr["nome"] = "Município " + terr["municipio_residencia"]
    terr["crescimento_pct"] = 0.0  # será calculado quando houver série temporal longa por município
    terr = terr.sort_values("score", ascending=False)

    # Mantém colunas que o app atual já lê + colunas técnicas extras.
    return terr[["uf", "nome", "crescimento_pct", "score", "nivel", "municipio_residencia", "internacoes", "perm_media", "valor_total", "obitos"]]


def pop_60_brasil_anual() -> pd.DataFrame:
    anos_anc = sorted(POP_60_BRASIL)
    anos = list(range(anos_anc[0], anos_anc[-1] + 1))
    valores = np.interp(anos, anos_anc, [POP_60_BRASIL[a] for a in anos_anc])
    return pd.DataFrame({"ano": anos, "pop_60_mais_milhoes": np.round(valores, 2)})


def projetar_brasil(taxa: float, fonte_taxa: str) -> pd.DataFrame:
    pop = pop_60_brasil_anual()
    pop["taxa_por_100k"] = round(taxa, 2)
    pop["fonte_taxa"] = fonte_taxa
    pop["internacoes_proj"] = (pop["pop_60_mais_milhoes"] * 1e6 / 1e5 * taxa).round().astype(int)

    for nome, reajuste in CENARIOS_SIGTAP.items():
        anos_frente = (pop["ano"] - ANO_BASE).clip(lower=0)
        valor = VALOR_MEDIO_BASE * (1 + reajuste) ** anos_frente
        pop[f"custo_{nome}"] = (pop["internacoes_proj"] * valor).round(2)

    pop["eh_projecao"] = (pop["ano"] > ANO_BASE).astype(int)
    return pop


def tendencia_linear(proj: pd.DataFrame) -> float:
    X = proj[["ano"]].values
    y = proj["internacoes_proj"].values
    return float(LinearRegression().fit(X, y).coef_[0])


def main() -> None:
    df = _ler_internacoes()

    hist = construir_historico(df)
    hist.to_csv(os.path.join(OUTPUT_PROC, "historico_indicadores.csv"), index=False)
    print("\n[Histórico observado]")
    print(hist.to_string(index=False))

    comorb = gerar_comorbidades_reais(df)
    comorb.to_csv(os.path.join(OUTPUT_PROC, "comorbidades.csv"), index=False)
    print("\n[Comorbidades reais / causas principais quando demência é secundária]")
    print(comorb.head(10).to_string(index=False))

    territorio = gerar_ranking_territorial(df)
    territorio.to_csv(os.path.join(OUTPUT_PROC, "territorio_scores.csv"), index=False)
    print("\n[Ranking territorial real — top 10]")
    print(territorio.head(10).to_string(index=False))

    # A taxa ainda é premissa do protótipo; deixamos explícito para evidência.
    taxa = TAXA_OBSERVADA_FALLBACK
    fonte_taxa = "Premissa documentada do protótipo; recalibrar com população 60+ do recorte"
    proj = projetar_brasil(taxa, fonte_taxa)
    proj.to_csv(os.path.join(OUTPUT_PROC, "projecao_demencia_2050.csv"), index=False)

    print("\n[Projeção Brasil — marcos]")
    marcos = proj[proj["ano"].isin([2020, 2025, 2030, 2040, 2050])]
    print(marcos[["ano", "pop_60_mais_milhoes", "taxa_por_100k", "internacoes_proj"]].to_string(index=False))
    print(f"Inclinação média estimada: {tendencia_linear(proj):,.0f} AIH/ano")
    print("\n✓ Arquivos analíticos gerados em data/processed/")


if __name__ == "__main__":
    main()
