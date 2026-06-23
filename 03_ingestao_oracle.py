"""
╔════════════════════════════════════════════════════════════╗
║  MindLink — Ingestão Oracle Autonomous Database            ║
║  Demência (F00–F03 + G30) · base SP-município → Brasil      ║
║  Equipe She Leads · Oracle Challenge FIAP 2026              ║
╚════════════════════════════════════════════════════════════╝

Carrega no Oracle ADB os artefatos gerados pelo pipeline:
  mindlink_demencia_sp.parquet     → MINDLINK_INTERNACOES  (base auditável SP-mun.)
  historico_indicadores.csv        → MINDLINK_INDICADORES   (observado por ano)
  projecao_demencia_2050.csv       → MINDLINK_PROJECAO      (Brasil 2020-2050)
  territorio_scores.csv            → MINDLINK_TERRITORIO     (ranking por UF)
  comorbidades.csv                 → MINDLINK_COMORBIDADES   (DIAG_SECUN)

Pré-requisitos:
    pip install oracledb pandas pyarrow python-dotenv

.env na raiz:
    ORACLE_USER=ADMIN
    ORACLE_PASSWORD=...
    ORACLE_DSN=nomedb_high
    ORACLE_WALLET_PATH=./wallet
    ORACLE_WALLET_PASSWORD=...

Uso:
    python 03_ingestao_oracle.py
"""

import os
import math
import warnings
import pandas as pd

warnings.filterwarnings("ignore")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import oracledb
except ImportError:
    raise ImportError("Execute: pip install oracledb")

# ── Configuração ─────────────────────────────────────────────────────────────
ORACLE_USER = os.getenv("ORACLE_USER", "ADMIN")
ORACLE_PWD  = os.getenv("ORACLE_PASSWORD", "")
ORACLE_DSN  = os.getenv("ORACLE_DSN", "")
WALLET_PATH = os.getenv("ORACLE_WALLET_PATH", "")
WALLET_PWD  = os.getenv("ORACLE_WALLET_PASSWORD", "")

OUTPUT_PROC = "data/processed/"
BATCH_SIZE  = 500

ARQ = {
    "internacoes": os.path.join(OUTPUT_PROC, "mindlink_demencia_sp.parquet"),
    "historico":   os.path.join(OUTPUT_PROC, "historico_indicadores.csv"),
    "projecao":    os.path.join(OUTPUT_PROC, "projecao_demencia_2050.csv"),
    "territorio":  os.path.join(OUTPUT_PROC, "territorio_scores.csv"),
    "comorbidades":os.path.join(OUTPUT_PROC, "comorbidades.csv"),
}


# ── DDL ──────────────────────────────────────────────────────────────────────
DDL = [
    """
    CREATE TABLE MINDLINK_INTERNACOES (
        id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        cid_principal        VARCHAR2(10),
        cid_grupo            VARCHAR2(5),
        cid_label            VARCHAR2(60),
        municipio_residencia VARCHAR2(10),
        ano                  NUMBER(4),
        mes                  NUMBER(2),
        dias_permanencia     NUMBER(5),
        valor_total          NUMBER(15,2),
        idade                NUMBER(3),
        faixa_etaria         VARCHAR2(10),
        sexo                 VARCHAR2(3),
        sexo_label           VARCHAR2(12),
        cnes_hospital        VARCHAR2(10),
        obito                NUMBER(1)
    )
    """,
    """
    CREATE TABLE MINDLINK_INDICADORES (
        ano          NUMBER(4) PRIMARY KEY,
        internacoes  NUMBER(12),
        valor_medio  NUMBER(15,2),
        perm_media   NUMBER(8,2)
    )
    """,
    """
    CREATE TABLE MINDLINK_PROJECAO (
        ano                 NUMBER(4) PRIMARY KEY,
        pop_60_mais_milhoes NUMBER(8,2),
        taxa_por_100k       NUMBER(8,2),
        internacoes_proj    NUMBER(12),
        custo_a_congelado   NUMBER(18,2),
        custo_b_parcial     NUMBER(18,2),
        custo_c_pleno       NUMBER(18,2),
        eh_projecao         NUMBER(1)
    )
    """,
    """
    CREATE TABLE MINDLINK_TERRITORIO (
        uf              VARCHAR2(2) PRIMARY KEY,
        nome            VARCHAR2(40),
        crescimento_pct NUMBER(5,1),
        score           NUMBER(5),
        nivel           VARCHAR2(15)
    )
    """,
    """
    CREATE TABLE MINDLINK_COMORBIDADES (
        cid_secundario VARCHAR2(10) PRIMARY KEY,
        descricao      VARCHAR2(60),
        internacoes    NUMBER(12)
    )
    """,
]

VIEWS = [
    """
    CREATE OR REPLACE VIEW VW_INTERNACOES_AGRUPADAS AS
    SELECT ano, cid_grupo, cid_label, faixa_etaria,
        COUNT(*)                          AS internacoes,
        SUM(valor_total)                  AS custo_total_rs,
        ROUND(AVG(valor_total), 2)        AS custo_medio_rs,
        ROUND(AVG(dias_permanencia), 1)   AS media_dias_perm,
        SUM(obito)                        AS total_obitos
    FROM MINDLINK_INTERNACOES
    GROUP BY ano, cid_grupo, cid_label, faixa_etaria
    ORDER BY ano
    """,
    """
    CREATE OR REPLACE VIEW VW_KPIS_EXECUTIVOS AS
    SELECT ano, internacoes_proj AS internacoes,
        ROUND(custo_a_congelado/1e6, 2) AS custo_cenario_a_milhoes,
        ROUND(custo_c_pleno/1e6, 2)     AS custo_cenario_c_milhoes,
        taxa_por_100k, pop_60_mais_milhoes, eh_projecao
    FROM MINDLINK_PROJECAO
    ORDER BY ano
    """,
]


# ── Conexão ──────────────────────────────────────────────────────────────────
def conectar() -> "oracledb.Connection":
    if WALLET_PATH and os.path.isdir(WALLET_PATH):
        print(f"[Oracle] Conectando com Wallet: {WALLET_PATH}")
        conn = oracledb.connect(user=ORACLE_USER, password=ORACLE_PWD, dsn=ORACLE_DSN,
                                config_dir=WALLET_PATH, wallet_location=WALLET_PATH,
                                wallet_password=WALLET_PWD)
    else:
        print("[Oracle] Conectando sem Wallet (TCP direto)...")
        conn = oracledb.connect(user=ORACLE_USER, password=ORACLE_PWD, dsn=ORACLE_DSN)
    print(f"[Oracle] ✅ Conectado — versão {conn.version}")
    return conn


def criar_estrutura(conn):
    with conn.cursor() as cur:
        for ddl in DDL:
            nome = [w for w in ddl.split()
                    if w.upper() not in ("CREATE", "TABLE", "IF", "NOT", "EXISTS")][0]
            try:
                cur.execute(ddl)
                print(f"[DDL] Tabela {nome} criada.")
            except oracledb.DatabaseError as e:
                if "ORA-00955" in str(e):
                    print(f"[DDL] Tabela {nome} já existe (ok).")
                else:
                    raise
        for view_sql in VIEWS:
            nome_view = view_sql.strip().split()[4]
            try:
                cur.execute(view_sql)
                print(f"[DDL] View {nome_view} criada/substituída.")
            except oracledb.DatabaseError as e:
                print(f"[DDL] Erro na view {nome_view}: {e}")
    conn.commit()
    print("[DDL] ✅ Estrutura criada.\n")


# ── Inserção em lote ──────────────────────────────────────────────────────────
def inserir_df(df, tabela, colunas, conn):
    cols = [c for c in colunas if c in df.columns]
    if not cols:
        print(f"  [{tabela}] ⚠ nenhuma coluna esperada — pulando.")
        return
    df_ins = df[cols].copy().where(pd.notnull(df[cols]), None)
    cols_sql = ", ".join(df_ins.columns).upper()
    ph = ", ".join([f":{i+1}" for i in range(len(df_ins.columns))])
    sql = f"INSERT INTO {tabela} ({cols_sql}) VALUES ({ph})"
    rows = [tuple(r) for r in df_ins.itertuples(index=False)]
    total = len(rows)
    with conn.cursor() as cur:
        for b in range(math.ceil(total / BATCH_SIZE) if total else 0):
            cur.executemany(sql, rows[b*BATCH_SIZE:(b+1)*BATCH_SIZE])
            print(f"  [{tabela}] {min((b+1)*BATCH_SIZE, total):,}/{total:,}", end="\r")
    conn.commit()
    print(f"\n  ✅ {total:,} registros → {tabela}")


def ingerir(chave, tabela, colunas, conn, leitor):
    caminho = ARQ[chave]
    if not os.path.exists(caminho):
        print(f"  [{tabela}] ⚠ {os.path.basename(caminho)} ausente — etapa pulada.")
        return
    df = leitor(caminho)
    inserir_df(df, tabela, colunas, conn)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    conn = conectar()
    criar_estrutura(conn)

    ingerir("internacoes", "MINDLINK_INTERNACOES",
            ["cid_principal", "cid_grupo", "cid_label", "municipio_residencia",
             "ano", "mes", "dias_permanencia", "valor_total", "idade",
             "faixa_etaria", "sexo", "sexo_label", "cnes_hospital", "obito"],
            conn, pd.read_parquet)

    ingerir("historico", "MINDLINK_INDICADORES",
            ["ano", "internacoes", "valor_medio", "perm_media"],
            conn, pd.read_csv)

    ingerir("projecao", "MINDLINK_PROJECAO",
            ["ano", "pop_60_mais_milhoes", "taxa_por_100k", "internacoes_proj",
             "custo_a_congelado", "custo_b_parcial", "custo_c_pleno", "eh_projecao"],
            conn, lambda p: pd.read_csv(p).rename(columns={
                "custo_A_congelado": "custo_a_congelado",
                "custo_B_parcial":   "custo_b_parcial",
                "custo_C_pleno":     "custo_c_pleno"}))

    ingerir("territorio", "MINDLINK_TERRITORIO",
            ["uf", "nome", "crescimento_pct", "score", "nivel"],
            conn, pd.read_csv)

    ingerir("comorbidades", "MINDLINK_COMORBIDADES",
            ["cid_secundario", "descricao", "internacoes"],
            conn, pd.read_csv)

    conn.close()
    print("\n✅ Pipeline de ingestão Oracle concluído!")


if __name__ == "__main__":
    main()