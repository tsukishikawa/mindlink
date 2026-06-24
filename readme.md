# 🧠 MindLink — Painel Analítico-Preditivo de Demência no SUS

**Challenge Oracle + FIAP 2026 · Equipe She Leads - Fase 03**

Plataforma de inteligência preditiva que antecipa a pressão das internações por
demência no SUS, traduzindo dados abertos do DATASUS em sinais de risco para o
gestor público — **antes** da sobrecarga acontecer.

> A demência é um risco previsível. O SUS precisa enxergar antes de saturar.

---

## 🎯 O problema

O Brasil envelhece em ritmo acelerado: a população 60+ salta de **29,9 milhões
(2020) para 64,5 milhões (2050)** — e as internações por demência acompanham essa
curva (+116% no período). O SUS, hoje, enxerga isso só no retrovisor: relatórios
descritivos do que **já** saturou. A MindLink projeta **onde vai saturar**, com
uma janela de manobra orçamentária real.

A MindLink **não é um BI**. BI descreve o passado; a MindLink projeta o futuro,
respondendo perguntas em linguagem natural via Oracle Select AI.

---

## 🏗️ Arquitetura

```
DATASUS / IBGE  →  Pipeline Python  →  Oracle Autonomous DB  →  Select AI (Gemini)
   (fontes)        (PySUS · ML)         (5 tabelas + views)        (pergunta → SQL)
                                               │
                                               ▼
                                    Flask (app.py) + Dashboard (Chart.js)
                                               │
                                               ▼
                                         Gestor público
```

Recorte clínico: **CID-10 F00–F03 + G30**. Base observada em **SP-município**
(taxa de 24,25 AIH/100 mil hab. 60+), projetada nacionalmente com a população
do IBGE. Diagrama completo em `docs/` (PPTX).

---

## 🧰 Stack tecnológica

| Camada | Tecnologia | Papel |
|---|---|---|
| Coleta | **PySUS · Python · pandas** | Extração das AIH (SIH-SUS), filtro CID F00–F03 + G30 |
| Modelagem | **scikit-learn · NumPy · pyarrow** | Projeção 2020–2050 (taxa × população IBGE) |
| Banco | **Oracle Autonomous Database** | 5 tabelas + 2 views, auto-tuning, JSON nativo |
| IA | **Oracle Select AI · Google Gemini** | Pergunta em português → SQL → resposta (`gemini-2.5-flash`) |
| Backend | **Flask · oracledb** | APIs de dados e do Select AI (conexão mTLS) |
| Frontend | **HTML · Chart.js** | Dashboard interativo + chat de IA |
| Segurança | **Oracle Wallet (mTLS/TLS)** | Conexão segura ao Autonomous DB |
| DevOps | **GitHub · VS Code** | Versionamento e documentação |

---

## 📂 Estrutura do projeto

```
mindlink-prototype/
├── app.py                    # backend Flask (dashboard + Select AI)
├── 01_coleta_pysus.py        # coleta SIH-SUS → parquet
├── 02_modelo_preditivo.py    # projeção 2020–2050 → CSVs
├── 03_ingestao_oracle.py     # ingestão no Oracle ADB
├── requirements.txt
├── .env                      # credenciais (NÃO versionar)
├── .gitignore
├── templates/
│   └── dashboard.html        # painel + chat (servido pelo Flask)
├── wallet/                   # wallet Oracle (NÃO versionar)
├── data/{raw,processed}/     # dados (regeneráveis)
├── sql/
│   └── select_ai_config.sql  # perfil Select AI + perguntas
└── docs/                     # deck, diagrama de arquitetura
```

---

## 🚀 Como rodar

### 1. Ambiente

```bash
python -m venv venv_mindlink
# Windows:
.\venv_mindlink\Scripts\activate
pip install -r requirements.txt
```

### 2. Oracle Autonomous Database

Crie um Autonomous Database (Always Free), baixe o **Wallet** para `wallet/` e
preencha o `.env`:

```env
ORACLE_USER=ADMIN
ORACLE_PASSWORD=sua_senha
ORACLE_DSN=seudb_high
ORACLE_WALLET_PATH=./wallet
ORACLE_WALLET_PASSWORD=senha_do_wallet
```

### 3. Pipeline de dados (na raiz do projeto)

```bash
python 01_coleta_pysus.py      # 1ª vez: teste com ANOS=[2024], MESES=[1]
python 02_modelo_preditivo.py
python 03_ingestao_oracle.py
```

### 4. Select AI (linguagem natural)

No SQL Worksheet do banco, rode `sql/select_ai_config.sql`. Configuração que
funciona em conta Free Tier (região SP): provedor **Google Gemini**, chave
gratuita do [AI Studio](https://aistudio.google.com), profile **`MINDLINK_GEMINI`**,
modelo `gemini-2.5-flash`.

### 5. Dashboard + Select AI

```bash
python app.py
# abre http://127.0.0.1:5000
```

O dashboard lê os dados ao vivo do Oracle e inclui a caixa "Pergunte em
português", que chama o Select AI e responde na mesma tela.

---

## 📊 Dados e fontes

- **SIH-SUS / DATASUS** (AIH) via PySUS — internações por demência.
- **IBGE Projeções da População, Revisão 2024** — denominadores 60+.
- Recorte: município de São Paulo · CID-10 **F00–F03 + G30** · 2020–2025.

---

## ⚠️ Limitações

- DATASUS opera com 2–3 meses de defasagem; não é tempo real.
- Filtro por `DIAG_PRINC` subnotifica a demência como comorbidade
  (`DIAG_SECUN`) — achado a ser explorado na evolução do projeto.
- Taxa de SP-município aplicada ao Brasil é premissa conservadora.
- Tabela SIGTAP defasada: custo projetado em cenários A/B/C.

*Não entregamos certeza. Entregamos probabilidade auditável.*

---

## 👥 Equipe She Leads

Ana Júlia Amorim · Mariana Ishikawa · Luana Ramos Rabelo ·
Beatriz Dias da Silva · Sthefany Feitosa da Silva

---

*Dado público bem usado melhora políticas públicas.*
