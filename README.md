<div align="center">

<img src="docs/assets/mindlink-header.svg" alt="MindLink — Mental Insight, Data Connection" width="100%">

<br>

![Python](https://img.shields.io/badge/Python-1E3A5F?style=for-the-badge&logo=python&logoColor=white)
![Oracle](https://img.shields.io/badge/Oracle_26ai-E07856?style=for-the-badge&logo=oracle&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache_Airflow-0E7C7B?style=for-the-badge&logo=apacheairflow&logoColor=white)
![Status](https://img.shields.io/badge/status-prova_de_conceito-2D3142?style=for-the-badge)

**Dados públicos para enxergar pressão hospitalar antes que ela vire crise**

[Visão geral](#visão-geral) · [Arquitetura](#arquitetura-lambda) · [Execução](#execução-local) · [Oracle](#oracle) · [Documentação](#documentação) · [Equipe](#equipe-she-leads)

</div>

---

## Visão geral

Imagine que cada hospital seja uma caixa-d'água. As internações entram, os leitos representam a capacidade e os dias de permanência mostram por quanto tempo essa capacidade fica ocupada.

Os dados existem em lugares diferentes e chegam com atraso. A **MindLink** organiza essas informações para ajudar o gestor a perceber onde a pressão associada à demência está crescendo — sem tratar uma estimativa como se fosse disponibilidade de leito em tempo real.

> [!IMPORTANT]
> A MindLink não decide para onde um paciente deve ir. Ela transforma dados públicos em uma sinalização auditável para apoiar o planejamento.

### O que o projeto faz

| Etapa | Entrega |
|:---:|---|
| **01 · Coleta** | Lê internações do SIH/SUS e identifica os CIDs `F00`, `F01`, `F02`, `F03` e `G30`. |
| **02 · Critério clínico** | Considera demência no diagnóstico principal e nos diagnósticos secundários. |
| **03 · Tratamento** | Padroniza município, hospital, competência, faixa etária, permanência, valor e óbito. |
| **04 · Disponibilização** | Agrega no mesmo grão do modelo Oracle e produz staging, validações e evidências. |

---

## Estado atual

> [!NOTE]
> **Implementado**, **executado**, **evidenciado** e **planejado** não significam a mesma coisa. A distinção abaixo protege a transparência técnica do projeto.

| Componente | Situação | O que podemos afirmar |
|---|---|---|
| ETL Python em modo demonstrativo | **Executado e testado** | O fluxo completo gera dados sintéticos determinísticos, valida qualidade e produz as stagings esperadas. |
| ETL com PySUS | **Implementado, dependente da fonte** | O código aceita coleta por UF, ano e mês. A execução depende da disponibilidade do PySUS/DATASUS e dos arquivos auxiliares de CNES e CID. |
| Apache Airflow | **Executado** | A DAG executou o ETL demonstrativo e validou a conexão com o Oracle. |
| Oracle Autonomous Database | **Evidenciado na Sprint 3** | Staging, dimensões, fatos e views foram apresentados no ambiente da equipe. Nesta revisão, o acesso Oracle está indisponível e não foi reexecutado. |
| Contagem de 3.305 registros | **Validada pela DAG** | A DAG consultou a staging Oracle já existente e confirmou `3.305` registros. Ela não carregou esses registros nessa mesma execução. |
| Select AI | **Dependente do ambiente Oracle** | As perguntas e consultas de referência existem, mas a execução ao vivo exige perfil, credencial e acesso ao banco. |
| Previsão de 1 a 3 meses | **Pesquisa/protótipo** | Há estrutura de dados e notebook analítico; não existe, neste repositório, um modelo preditivo de produção validado. |
| Dashboard | **Protótipo separado** | A interface da fase anterior é demonstrativa e não é apresentada aqui como painel Oracle ao vivo. |

---

## Arquitetura Lambda

A MindLink adotou a arquitetura Lambda porque trabalha principalmente com bases públicas mensais, que precisam de histórico, reprocessamento e rastreabilidade. A camada batch está implementada. A camada de velocidade permanece prevista para fontes futuras mais frequentes; não há alegação de streaming em tempo real.

```mermaid
flowchart LR
    A["SIH/SUS<br/>CNES · CID-10"] --> B["Batch Layer<br/>Python · Pandas · PySUS"]
    B --> C["Qualidade<br/>e staging"]
    C --> D["Serving Layer<br/>Oracle 26ai"]
    D --> E["Views · análises<br/>Select AI"]
    F["Speed Layer<br/>futura"] -.-> D

    style A fill:#F5F2EC,stroke:#1E3A5F,color:#2D3142
    style B fill:#0E7C7B,stroke:#0E7C7B,color:#fff
    style C fill:#F5F2EC,stroke:#E07856,color:#2D3142
    style D fill:#1E3A5F,stroke:#1E3A5F,color:#fff
    style E fill:#F5F2EC,stroke:#0E7C7B,color:#2D3142
    style F fill:#F5F2EC,stroke:#2D3142,color:#2D3142
```

<details>
<summary><strong>Entenda cada camada em linguagem simples</strong></summary>

<br>

- **Batch Layer:** organiza o histórico completo, como quem fecha e confere o estoque do mês.
- **Serving Layer:** deixa os dados prontos para consulta, como uma prateleira organizada.
- **Speed Layer futura:** serviria para atualizações mais rápidas, caso surjam fontes adequadas. Ela ainda não foi implementada.

</details>

Mais detalhes: [arquitetura técnica](docs/ARCHITECTURE.md).

---

## Recorte da prova de conceito

| Dimensão | Definição |
|---|---|
| **Território** | Estado de São Paulo |
| **Período documentado** | Competências `202401` a `202512` |
| **Unidade analítica** | Competência × município × CNES |
| **Fonte de internações** | SIH/SUS, acessado programaticamente por PySUS quando disponível |
| **Capacidade hospitalar** | CNES |
| **Critério clínico** | CID-10 `F00`, `F01`, `F02`, `F03` e `G30` |
| **Diagnósticos** | Principal e secundários |
| **IBGE** | Referência metodológica; ainda não persiste como dimensão própria no modelo atual |

---

## Execução local

O modo demonstrativo prova o funcionamento do software sem internet, PySUS ou credenciais. Os valores gerados são **sintéticos** e não devem ser apresentados como resultado do SUS.

<details open>
<summary><strong>Executar a demonstração</strong></summary>

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows

pip install -r requirements.txt
python src/mindlink_etl_sprint3_oracle.py --demo
```

</details>

<details>
<summary><strong>Ver arquivos gerados</strong></summary>

```text
data/raw/mindlink_sih_raw_amostra.csv
data/processed/mindlink_internacoes_demencia_tratado.csv
data/processed/stg_mindlink_internacoes_python.csv
data/processed/stg_mindlink_comorbidades_python.csv
data/evidence/mindlink_resumo_etl.csv
```

</details>

<details>
<summary><strong>Executar testes automatizados</strong></summary>

```bash
pip install -r requirements-dev.txt
pytest
```

</details>

### Coleta real

O comando representa o caminho implementado para coleta real. Ele não faz parte do teste automatizado porque depende de disponibilidade externa e de arquivos oficiais auxiliares.

```bash
python src/mindlink_etl_sprint3_oracle.py \
  --uf SP \
  --anos 2024,2025 \
  --meses 1,2,3,4,5,6,7,8,9,10,11,12 \
  --cadastro-cnes-csv data/reference/cnes_lookup.csv \
  --cid-csv data/reference/cid10.csv
```

---

## Oracle

Os scripts oficiais estão separados por responsabilidade:

1. [`sql/01_ddl_mindlink_sprint3.sql`](sql/01_ddl_mindlink_sprint3.sql) cria staging, dimensões, fatos, índices e views.
2. [`sql/02_dml_mindlink_sprint3.sql`](sql/02_dml_mindlink_sprint3.sql) registra a carga utilizada na entrega e promove os dados para o modelo analítico.
3. O ETL Python pode carregar as stagings com `--oracle-load` quando o ambiente e as credenciais estiverem disponíveis.

> [!CAUTION]
> Credenciais, Wallet e arquivos brutos nunca devem ser versionados. Use [`.env.example`](.env.example) somente como referência para os nomes das variáveis.

---

## Estrutura do repositório

```text
mindlink/
├── src/                 ETL oficial da Sprint 3
├── dags/                DAG executada no Apache Airflow
├── sql/                 DDL e DML do modelo Oracle
├── notebooks/           análise estatística e experimentos
├── tests/               testes locais sem dependência do Oracle
├── docs/                arquitetura, status e matriz de evidências
├── data/                instruções; dados gerados não são versionados
└── docs/history/        entrega anterior preservada como contexto
```

## Documentação

| Documento | Finalidade |
|---|---|
| [Status técnico e limitações](docs/STATUS.md) | Situação real de cada componente |
| [Matriz de evidências](docs/EVIDENCE.md) | Relação entre alegações e comprovações |
| [Jornada da arquitetura Lambda](docs/ARCHITECTURE.md) | Decisões e fluxo técnico |
| [Evolução do repositório](docs/HISTORY.md) | Histórico das entregas |

---

## Limites de interpretação

> [!WARNING]
> Este projeto apoia planejamento. Ele não substitui regulação médica, decisão clínica ou informação hospitalar em tempo real.

- Cadastro de leitos não significa leito livre.
- A proxy de pressão não substitui regulação médica ou hospitalar.
- SIH/SUS e CNES não são fontes em tempo real.
- Diagnóstico secundário depende da qualidade de preenchimento da AIH.
- O recorte de CIDs é conservador e não cobre todas as etiologias de demência.
- Resultados de São Paulo não devem ser extrapolados automaticamente para todo o Brasil.
- Dados sintéticos do modo `--demo` servem somente para teste do código.

---

## Equipe She Leads

| Integrante | RM |
|---|---:|
| **Ana Júlia Amorim** | 572387 |
| **Beatriz Dias da Silva** | 569873 |
| **Luana Ramos Rabelo** | 570351 |
| **Mariana Ishikawa** | 572886 |
| **Sthefany Feitosa da Silva** | 568651 |

<div align="center">

**Challenge Oracle + FIAP 2026**

*MindLink transforma insight em conexão.*

</div>
