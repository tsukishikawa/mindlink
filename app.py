"""
╔════════════════════════════════════════════════════════════╗
║  MindLink — Backend (Flask) : Dashboard + Select AI         ║
║  Conecta no Oracle como ADMIN (mesmo .env do 03)            ║
║  Equipe She Leads · Oracle Challenge FIAP 2026              ║
╚════════════════════════════════════════════════════════════╝

Serve o dashboard e expõe 2 APIs:
  GET  /api/data   → dados dos gráficos (lê as views/tabelas)
  POST /api/ask    → pergunta em português → Select AI (Gemini)

Como conecta via ADMIN, NÃO precisa de grants nem prefixo ADMIN. — tudo é
acessível direto, e o profile MINDLINK_GEMINI (criado no ADMIN) funciona.

Instalação:
    pip install flask oracledb python-dotenv

.env (o mesmo do 03_ingestao_oracle.py):
    ORACLE_USER=ADMIN
    ORACLE_PASSWORD=...
    ORACLE_DSN=nomedb_high
    ORACLE_WALLET_PATH=./wallet
    ORACLE_WALLET_PASSWORD=...
    MINDLINK_AI_PROFILE=MINDLINK_GEMINI   (opcional; default já é esse)

Uso:
    python app.py
    # abre http://127.0.0.1:5000
"""

import os
from flask import Flask, jsonify, request, render_template

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import oracledb
# CLOB volta como string (resposta do Select AI), não como objeto LOB
oracledb.defaults.fetch_lobs = False

# ── Configuração ─────────────────────────────────────────────────────────────
USER    = os.getenv("ORACLE_USER", "ADMIN")
PWD     = os.getenv("ORACLE_PASSWORD", "")
DSN     = os.getenv("ORACLE_DSN", "")
WALLET  = os.getenv("ORACLE_WALLET_PATH", "")
WPWD    = os.getenv("ORACLE_WALLET_PASSWORD", "")
PROFILE = os.getenv("MINDLINK_AI_PROFILE", "MINDLINK_GEMINI")

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_wallet():
    """Resolve a pasta do wallet (relativa ao app.py) e confirma que existe."""
    if not WALLET:
        return None
    p = WALLET if os.path.isabs(WALLET) else os.path.join(BASE_DIR, WALLET)
    if not os.path.isdir(p):
        return None
    # config_dir tem que ser a pasta que CONTÉM o tnsnames.ora.
    # Se o zip foi extraído numa subpasta, procura o tnsnames.ora um nível abaixo.
    if os.path.isfile(os.path.join(p, "tnsnames.ora")):
        return p
    for nome in os.listdir(p):
        sub = os.path.join(p, nome)
        if os.path.isdir(sub) and os.path.isfile(os.path.join(sub, "tnsnames.ora")):
            return sub
    return p  # devolve mesmo assim; o erro de conexão será mais específico


def get_conn():
    w = _resolve_wallet()
    if not w:
        raise RuntimeError(
            f"Wallet não encontrado. ORACLE_WALLET_PATH='{WALLET}' "
            f"(resolvido a partir de {BASE_DIR}). Coloque a pasta do wallet "
            f"(a que contém tnsnames.ora) ao lado do app.py e ajuste o .env.")
    return oracledb.connect(user=USER, password=PWD, dsn=DSN,
                            config_dir=w, wallet_location=w, wallet_password=WPWD)


def query(sql, params=None):
    """Roda um SELECT e devolve lista de dicionários (coluna→valor)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ── Página ───────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("dashboard.html")


# ── API: dados dos gráficos ──────────────────────────────────────────────────
@app.route("/api/data")
def data():
    try:
        projecao = query("""
            SELECT ano, pop_60_mais_milhoes, internacoes_proj,
                   custo_a_congelado, custo_c_pleno, eh_projecao
            FROM   MINDLINK_PROJECAO ORDER BY ano""")
        territorio = query("""
            SELECT uf, nome, crescimento_pct, score, nivel
            FROM   MINDLINK_TERRITORIO ORDER BY score DESC""")
        comorbidades = query("""
            SELECT cid_secundario, descricao, internacoes
            FROM   MINDLINK_COMORBIDADES ORDER BY internacoes DESC""")
        cid = query("""
            SELECT cid_label, SUM(internacoes) AS total
            FROM   VW_INTERNACOES_AGRUPADAS GROUP BY cid_label ORDER BY total DESC""")
        return jsonify({"projecao": projecao, "territorio": territorio,
                        "comorbidades": comorbidades, "cid": cid})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# ── API: Select AI ───────────────────────────────────────────────────────────
@app.route("/api/ask", methods=["POST"])
def ask():
    pergunta = (request.get_json(silent=True) or {}).get("pergunta", "").strip()
    if not pergunta:
        return jsonify({"erro": "pergunta vazia"}), 400
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT DBMS_CLOUD_AI.GENERATE("
                "  prompt => :p, profile_name => :prof, action => 'narrate') "
                "FROM dual",
                {"p": pergunta, "prof": PROFILE})
            resposta = cur.fetchone()[0]
        return jsonify({"resposta": resposta})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)