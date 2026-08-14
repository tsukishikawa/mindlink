# MindLink — Painel Analítico-Preditivo de Demência no SUS em SP

**Challenge Oracle + FIAP 2026 · Equipe She Leads · Sprint 3**

Plataforma de inteligência analítica e preditiva que antecipa a pressão das internações por demência no SUS, traduzindo dados públicos do DATASUS em sinais de risco para o gestor público **antes** da sobrecarga acontecer.

> A demência é um risco previsível. O SUS precisa enxergar antes de saturar.

---

## Visão geral

A MindLink nasce para apoiar secretarias de saúde, gestores públicos, tribunais de contas e equipes de planejamento na identificação de territórios com maior risco de aumento de internações associadas à demência.

A proposta da Sprint 3 é sair do protótipo conceitual e validar uma arquitetura mínima funcional com dados reais, usando uma base comum para todas as disciplinas:

```text
DATASUS / SIH-SUS / CNES
↓
Python + PySUS + pandas
↓
Tratamento, filtros CID-10 e validação
↓
Oracle Autonomous Database
↓
Select AI + Dashboard
↓
Gestor público
```

A MindLink **não é apenas um BI**. BI descreve o passado; a MindLink organiza dados públicos, evidencia padrões territoriais e prepara a base para projeções de demanda hospitalar.

---

## Problema

O Brasil envelhece em ritmo acelerado. A população 60+ cresce de forma consistente, e a pressão sobre o SUS tende a aumentar em internações associadas a demência, fragilidade, pneumonia, infecção urinária, quedas e outras condições frequentes em idosos.

O desafio é que a demência nem sempre aparece como diagnóstico principal da internação. Muitas vezes ela surge como diagnóstico secundário ou comorbidade, o que pode gerar subnotificação em análises tradicionais.

Por isso, a Sprint 3 da MindLink compara dois caminhos metodológicos:

```text
1. DIAG_PRINC
2. DIAG_PRINC + DIAG_SECUN
```

Essa comparação é central para revelar uma população que pode ficar invisível em painéis tradicionais baseados apenas no diagnóstico principal.

---

## Recorte da Sprint 3

| Dimensão | Definição |
|---|---|
| Território | São Paulo, com possibilidade de teste por município |
| Fonte principal | SIH/SUS via PySUS |
| Fonte complementar | CNES via PySUS |
| Período inicial | Teste com recorte pequeno antes de expansão histórica |
| Período-alvo | 2020–2025, conforme viabilidade dos dados |
| CIDs de demência | F00, F01, F02, F03 e G30 |
| Comparação metodológica | DIAG_PRINC versus DIAG_PRINC + DIAG_SECUN |
| Banco | Oracle Autonomous Database |
| IA analítica | Oracle Select AI |

---

## Arquitetura da solução

```text
FONTES PÚBLICAS
SIH/SUS · CNES · IBGE
        ↓
INGESTÃO
Python · PySUS
        ↓
TRANSFORMAÇÃO
pandas · filtros CID-10 · padronização de colunas
        ↓
VALIDAÇÃO
missings · outliers · distribuição · consistência temporal
        ↓
BANCO ANALÍTICO
Oracle Autonomous Database
        ↓
CAMADA SEMÂNTICA
DDL · DML · COMMENTS · views · modelo relacional
        ↓
CONSUMO
Select AI · Flask · Dashboard
        ↓
DECISÃO
Gestor público · planejamento · orçamento · fiscalização
```

A arquitetura é única. Cada disciplina da Sprint 3 avalia uma evidência diferente dessa mesma solução:

| Bloco | O que entrega | Disciplinas que alimenta |
|---|---|---|
| Dados reais e recorte | Fonte, período, território, CIDs e colunas | Nemec, Rita, Patrícia |
| Pipeline Python/PySUS | Coleta e tratamento dos dados reais | Patrícia, Milton, Nemec |
| Modelo de dados e Oracle | Tabelas, DDL, DML, PK/FK e carga | Rita, Oracle/Data Architecture |
| Validação/AED | Distribuição, missings, outliers e padrões | Nemec |
| Select AI e dashboard | Perguntas reais sobre a base modelada | Oracle/Data Architecture, Rita, Sprint 4 |
| Governança e evidências | LGPD, COBIT, rastreabilidade e prints | Selas e todas |

---

## Stack tecnológica

| Camada | Tecnologia | Papel na MindLink |
|---|---|---|
| Fonte | DATASUS / SIH-SUS | Internações hospitalares e diagnósticos |
| Fonte | CNES | Estabelecimentos, hospitais e capacidade assistencial |
| Fonte opcional | IBGE | População e denominadores demográficos |
| Ingestão | PySUS | Acesso programático às bases públicas |
| Transformação | Python + pandas | Limpeza, filtros CID-10, agregações e indicadores |
| Modelagem | NumPy + scikit-learn | Projeções, tendências e análises de sensibilidade |
| Banco | Oracle Autonomous Database | Persistência analítica e estrutura relacional |
| IA | Oracle Select AI | Perguntas em linguagem natural sobre a base modelada |
| Backend | Flask + oracledb | API para dashboard e Select AI |
| Frontend | HTML + Chart.js | Dashboard e visualizações executivas |
| Orquestração | Apache Airflow | DAG conceitual/operacional do pipeline |
| Segurança | Oracle Wallet / TLS | Conexão segura com o banco |
| Versionamento | GitHub | Rastreabilidade técnica do projeto |

---

## Estrutura do projeto

```text
mindlink/
├── 01_coleta_pysus.py              # coleta SIH/SUS via PySUS e filtra demência
├── 02_modelo_preditivo.py          # gera projeções, indicadores e sensibilidade
├── 03_ingestao_oracle.py           # cria/carga tabelas no Oracle Autonomous DB
├── 04_coleta_cnes.py               # coleta CNES e prepara capacidade hospitalar
├── app.py                          # backend Flask do dashboard e Select AI
├── requirements.txt                # dependências Python
├── readme.md                       # documentação principal do projeto
├── README_SPRINT3_PATCH.md         # resumo dos ajustes técnicos da Sprint 3
├── .gitignore                      # evita versionar dados sensíveis/gerados
│
├── dags/
│   └── mindlink_pipeline_dag.py    # DAG do Airflow para o pipeline da Sprint 3
│
├── docs/
│   ├── Sprint3_Ajustes_Arquitetura.md
│   └── ...                         # evidências, deck e documentação técnica
│
├── sql/
│   ├── 01_ddl_mindlink_dimensional.sql
│   ├── 02_comments_mindlink.sql
│   ├── 03_select_ai_perguntas.sql
│   └── select_ai_config.sql
│
├── templates/
│   └── dashboard.html              # interface do dashboard Flask
│
├── data/                           # gerado localmente, não versionar
│   ├── raw/
│   └── processed/
│
└── wallet/                         # wallet Oracle local, não versionar
```

> **Importante:** `data/`, `wallet/`, `.env`, `venv/` e `__pycache__/` não devem ser enviados ao GitHub.

---

## Papel dos principais arquivos

| Arquivo | Função |
|---|---|
| `01_coleta_pysus.py` | Baixa dados reais do SIH/SUS via PySUS, aplica filtros CID-10 e compara diagnóstico principal com diagnóstico secundário |
| `04_coleta_cnes.py` | Baixa/prepara dados do CNES para apoiar indicadores de capacidade hospitalar |
| `02_modelo_preditivo.py` | Consolida indicadores, gera projeções e arquivos derivados para análise |
| `03_ingestao_oracle.py` | Cria tabelas no Oracle Autonomous Database e carrega os dados tratados |
| `dags/mindlink_pipeline_dag.py` | Representa a orquestração do pipeline no Apache Airflow |
| `sql/01_ddl_mindlink_dimensional.sql` | Modelo relacional/dimensional para a entrega de banco |
| `sql/02_comments_mindlink.sql` | Comentários semânticos para apoiar Select AI e interpretação de negócio |
| `sql/03_select_ai_perguntas.sql` | Perguntas em linguagem natural e consultas esperadas para demonstração |
| `app.py` | Backend Flask para dashboard e endpoint de perguntas |

---

## Como rodar localmente

### 1. Criar ambiente Python

```bash
python -m venv venv_mindlink
```

Windows:

```bash
.\venv_mindlink\Scripts\activate
```

macOS/Linux:

```bash
source venv_mindlink/bin/activate
```

Instalar dependências:

```bash
pip install -r requirements.txt
```

---

### 2. Rodar o pipeline em recorte pequeno

Para teste inicial, use um recorte menor antes de rodar vários anos.

```bash
python 01_coleta_pysus.py
python 04_coleta_cnes.py
python 02_modelo_preditivo.py
```

Depois de validar o funcionamento, expandir o período conforme capacidade da máquina e disponibilidade do DATASUS.

---

### 3. Configurar Oracle Autonomous Database

Crie um Autonomous Database na OCI, baixe o Wallet e configure um arquivo `.env` local:

```text
ORACLE_USER=ADMIN
ORACLE_PASSWORD=sua_senha
ORACLE_DSN=seudb_high
ORACLE_WALLET_PATH=./wallet
ORACLE_WALLET_PASSWORD=senha_do_wallet
MINDLINK_AI_PROFILE=MINDLINK_GEMINI
```

Depois rode:

```bash
python 03_ingestao_oracle.py
```

---

### 4. Rodar SQLs da Sprint 3

No Oracle SQL Developer ou Database Actions, executar os scripts da pasta `sql/`:

```text
sql/01_ddl_mindlink_dimensional.sql
sql/02_comments_mindlink.sql
sql/03_select_ai_perguntas.sql
```

Esses arquivos apoiam principalmente as entregas de modelagem relacional, comentários semânticos e consultas com Select AI.

---

### 5. Rodar dashboard

```bash
python app.py
```

Acessar:

```text
http://127.0.0.1:5000
```

---

## Modelo de dados proposto

A Sprint 3 utiliza uma modelagem relacional/dimensional para organizar os dados em dimensões e fatos.

```text
dim_tempo
dim_municipio
dim_diagnostico
dim_faixa_etaria
dim_estabelecimento
fato_internacao_mensal
fato_capacidade_mensal
```

Esse modelo permite responder perguntas como:

- quais municípios apresentam crescimento de internações associadas à demência;
- quais diagnósticos apresentam maior permanência média;
- quais territórios têm maior pressão assistencial;
- qual a diferença entre analisar apenas `DIAG_PRINC` e analisar `DIAG_PRINC + DIAG_SECUN`;
- quais regiões exigem planejamento de leitos, equipes ou orçamento.

---

## Select AI — perguntas de demonstração

Exemplos de perguntas estratégicas que a base modelada deve responder:

```text
Quais municípios apresentam maior crescimento de internações associadas à demência?
```

```text
Qual a diferença entre considerar apenas diagnóstico principal e considerar diagnóstico principal mais secundário?
```

```text
Quais territórios apresentam maior pressão assistencial considerando internações e leitos SUS?
```

```text
Quais diagnósticos têm maior permanência média hospitalar no período analisado?
```

---

## Dados e fontes

- **SIH/SUS / DATASUS** — internações hospitalares e AIH via PySUS.
- **CNES / DATASUS** — estabelecimentos, hospitais e capacidade hospitalar via PySUS.
- **IBGE** — população e denominadores demográficos para projeções e taxas.

O CSV, quando gerado, é tratado como **produto intermediário do pipeline**, não como fonte manual principal. A fonte-mãe da Sprint 3 é:

```text
DATASUS → PySUS → pandas → Oracle
```

---

## Limitações e premissas

- O DATASUS não é uma base em tempo real e pode ter defasagem de processamento.
- A análise por `DIAG_PRINC` pode subestimar a presença da demência quando ela aparece como comorbidade.
- A expansão nacional deve ser feita depois da validação do recorte menor.
- Projeções dependem de premissas populacionais, clínicas e assistenciais.
- Indicadores de capacidade hospitalar dependem da qualidade e atualização dos dados CNES.

*Não entregamos certeza. Entregamos probabilidade auditável.*

---

## Relação com a Sprint 3

| Disciplina | Evidência no projeto |
|---|---|
| Smart SQL & Relational Databases | DDL, DML, importação, modelo relacional e dados válidos |
| Building Data-Driven Applications | Scripts Python, PySUS, pandas, execução e logs |
| Modern Data Architecture & Engineering | Arquitetura Lambda/Kappa, DAG e fluxo operacional |
| Data Architecture, Analytics & NoSQL Solutions | Oracle Autonomous Database, Wallet, COMMENTS e Select AI |
| Statistical Methods & Machine Learning | Dataset unificado, AED, distribuição, missings, outliers e projeção |
| Data Ethics, Governance & Security | LGPD, COBIT, rastreabilidade, riscos e evidências |

---

## Equipe She Leads

- Ana Júlia Amorim — RM 572387
- Beatriz Dias da Silva — RM 569873
- Luana Ramos Rabelo — RM 570351
- Mariana Ishikawa — RM 572886
- Sthefany Feitosa da Silva — RM 568651

---

*Dado público bem usado melhora políticas públicas.*
