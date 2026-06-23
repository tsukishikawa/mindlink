"""
╔════════════════════════════════════════════════════════════╗
║  MindLink — Modelo Preditivo de Demência (BRASIL)          ║
║  Projeção 2020–2050 · CID-10 F00–F03 + G30                  ║
║  Equipe She Leads · Oracle Challenge FIAP 2026              ║
╚════════════════════════════════════════════════════════════╝

Instalação:
    pip install pandas numpy scikit-learn pyarrow

Uso:
    python 02_modelo_preditivo.py
"""

import os
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

warnings.filterwarnings("ignore")

OUTPUT_PROC = "data/processed/"
ARQUIVO_INTERNACOES = os.path.join(OUTPUT_PROC, "mindlink_demencia_sp.parquet")

# ── Premissas do deck ────────────────────────────────────────────────────────
TAXA_OBSERVADA = 24.25     # AIH por 100 mil hab. 60+ (SP-município, DATASUS 2025)
ANO_BASE       = 2025      # ano de referência da taxa e do custo
ANO_FIM        = 2050      # horizonte da projeção

# População 60+ do Brasil (milhões) — IBGE Projeções Revisão 2024 (Censo 2022).
# Âncoras de 5 em 5 anos; o código interpola os anos intermediários.
POP_60_BRASIL = {
    2020: 29.9,
    2025: 34.6,
    2030: 40.3,
    2035: 47.1,
    2040: 53.7,
    2045: 59.1,   # interpolado entre 2040 e 2050
    2050: 64.5,
}

# Cenários de reajuste da tabela SIGTAP (custo por internação)
VALOR_MEDIO_BASE = 4000.0   # R$ por internação em 2025 (SP-município; ⚠ ajuste com dado real)
CENARIOS_SIGTAP = {
    "A_congelado": 0.000,   # sem reajuste — perde para a inflação (cenário do deck)
    "B_parcial":   0.0175,  # ~50% do IPCA
    "C_pleno":     0.035,   # IPCA pleno (3,5% a.a.)
}

# Ranking territorial simulado (deck, slide 13) — score 0-100 e crescimento projetado.
# Na versão com dado real o score vem de AIH × pop 60+ × permanência × custo × óbito × CNES.
TERRITORIO = pd.DataFrame([
    {"uf": "SP", "nome": "São Paulo",      "crescimento_pct": 22, "score": 91, "nivel": "Crítico"},
    {"uf": "RJ", "nome": "Rio de Janeiro", "crescimento_pct": 19, "score": 84, "nivel": "Alto"},
    {"uf": "MG", "nome": "Minas Gerais",   "crescimento_pct": 18, "score": 81, "nivel": "Alto"},
    {"uf": "BA", "nome": "Bahia",          "crescimento_pct": 15, "score": 74, "nivel": "Médio-Alto"},
    {"uf": "PR", "nome": "Paraná",         "crescimento_pct": 14, "score": 70, "nivel": "Médio"},
    {"uf": "PE", "nome": "Pernambuco",     "crescimento_pct": 13, "score": 67, "nivel": "Médio"},
])

# Condições associadas quando a demência aparece como diagnóstico SECUNDÁRIO
# (deck, slide 13) — o "universo oculto" revelado por DIAG_PRINC + DIAG_SECUN.
COMORBIDADES = pd.DataFrame([
    {"cid_secundario": "J18", "descricao": "Pneumonia",             "internacoes": 380},
    {"cid_secundario": "N39", "descricao": "Infecção urinária",     "internacoes": 210},
    {"cid_secundario": "J69", "descricao": "Pneumonite aspirativa", "internacoes": 165},
    {"cid_secundario": "S72", "descricao": "Fratura de fêmur",      "internacoes": 120},
    {"cid_secundario": "I63", "descricao": "AVC isquêmico",         "internacoes": 95},
    {"cid_secundario": "E86", "descricao": "Desidratação",          "internacoes": 70},
])


# ── Interpolação anual da população 60+ ──────────────────────────────────────
def pop_60_brasil_anual() -> pd.DataFrame:
    anos_anc = sorted(POP_60_BRASIL)
    anos = list(range(anos_anc[0], anos_anc[-1] + 1))
    valores = np.interp(anos, anos_anc, [POP_60_BRASIL[a] for a in anos_anc])
    return pd.DataFrame({"ano": anos, "pop_60_mais_milhoes": np.round(valores, 2)})


# ── Consolidação do histórico observado (SP-município) ───────────────────────
def construir_historico(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega as internações observadas em SP-município por ano.
    Serve de evidência da taxa e da curva de valor médio (defasagem SIGTAP).
    """
    agg = {"cid_principal": "count"}
    if "valor_total" in df.columns:
        agg["valor_total"] = "mean"
    if "dias_permanencia" in df.columns:
        agg["dias_permanencia"] = "mean"

    hist = df.groupby("ano").agg(**{
        "internacoes":      ("cid_principal", "count"),
        "valor_medio":      ("valor_total", "mean") if "valor_total" in df.columns else ("cid_principal", "size"),
        "perm_media":       ("dias_permanencia", "mean") if "dias_permanencia" in df.columns else ("cid_principal", "size"),
    }).reset_index()
    return hist


# ── Projeção nacional por taxa × população ───────────────────────────────────
def projetar_brasil(taxa: float) -> pd.DataFrame:
    """
    internacoes(ano) = pop_60+(ano) × taxa / 100.000
    Custo por cenário SIGTAP a partir do valor médio base.
    """
    pop = pop_60_brasil_anual()
    pop["taxa_por_100k"] = round(taxa, 2)
    # pop em milhões → habitantes; / 100.000 × taxa
    pop["internacoes_proj"] = (pop["pop_60_mais_milhoes"] * 1e6 / 1e5 * taxa).round().astype(int)

    for nome, reajuste in CENARIOS_SIGTAP.items():
        anos_frente = (pop["ano"] - ANO_BASE).clip(lower=0)
        valor = VALOR_MEDIO_BASE * (1 + reajuste) ** anos_frente
        pop[f"custo_{nome}"] = (pop["internacoes_proj"] * valor).round(2)

    pop["eh_projecao"] = (pop["ano"] > ANO_BASE).astype(int)
    return pop


# ── Tendência opcional (scikit-learn) — cross-check da curva ─────────────────
def tendencia_linear(proj: pd.DataFrame) -> float:
    """Ajusta uma reta sobre a projeção só para reportar a inclinação (AIH/ano)."""
    X = proj[["ano"]].values
    y = proj["internacoes_proj"].values
    m = LinearRegression().fit(X, y)
    return float(m.coef_[0])


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    taxa = TAXA_OBSERVADA

    # Histórico observado (se a coleta já rodou) — valida/recalibra a taxa
    if os.path.exists(ARQUIVO_INTERNACOES):
        df = pd.read_parquet(ARQUIVO_INTERNACOES)
        df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
        df = df.dropna(subset=["ano"]); df["ano"] = df["ano"].astype(int)
        hist = construir_historico(df)
        hist.to_csv(os.path.join(OUTPUT_PROC, "historico_indicadores.csv"), index=False)
        print("[Histórico observado · SP-município]")
        print(hist.to_string(index=False))
        print(f"\n[Taxa] Usando taxa documentada do deck: {taxa} AIH/100k 60+ "
              f"(recalibre com a população 60+ de SP-município se desejar).")
    else:
        print(f"[Aviso] {ARQUIVO_INTERNACOES} ausente — projetando só com a taxa do deck ({taxa}).")
        os.makedirs(OUTPUT_PROC, exist_ok=True)

    # Projeção nacional
    proj = projetar_brasil(taxa)
    proj.to_csv(os.path.join(OUTPUT_PROC, "projecao_demencia_2050.csv"), index=False)

    # Dados territoriais e de comorbidade do deck
    TERRITORIO.to_csv(os.path.join(OUTPUT_PROC, "territorio_scores.csv"), index=False)
    COMORBIDADES.to_csv(os.path.join(OUTPUT_PROC, "comorbidades.csv"), index=False)

    # Conferência contra os números do deck
    marcos = proj[proj["ano"].isin([2020, 2025, 2030, 2035, 2040, 2050])]
    print("\n[Projeção Brasil — conferência com o deck]")
    print(marcos[["ano", "pop_60_mais_milhoes", "internacoes_proj"]].to_string(index=False))
    i0 = proj.loc[proj["ano"] == 2020, "internacoes_proj"].iloc[0]
    i1 = proj.loc[proj["ano"] == 2050, "internacoes_proj"].iloc[0]
    print(f"\nCrescimento 2020→2050: {i0:,} → {i1:,}  (+{(i1/i0-1)*100:.0f}%)")
    print(f"Inclinação média (regressão linear): {tendencia_linear(proj):,.0f} AIH/ano")
    print(f"\n✓ Projeção salva: {os.path.join(OUTPUT_PROC, 'projecao_demencia_2050.csv')}")


if __name__ == "__main__":
    main()