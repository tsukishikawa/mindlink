# MindLink — Ajustes Sprint 3

## O que este patch corrige

Este pacote muda o foco do repositório para a arquitetura defendida na Sprint 3:

```text
DATASUS / SIH-SUS / CNES
↓
Python + PySUS + pandas
↓
comparação DIAG_PRINC vs DIAG_PRINC + DIAG_SECUN
↓
dataset tratado e auditável
↓
Oracle Autonomous Database
↓
Select AI + dashboard + evidências
```

## Por que isso é necessário

O repositório já tinha uma estrutura boa, com `01_coleta_pysus.py`, `02_modelo_preditivo.py`, `03_ingestao_oracle.py`, `app.py` e Select AI. O problema principal era que a coleta ainda filtrava apenas `DIAG_PRINC`, enquanto a tese da MindLink é justamente revelar a demência como comorbidade em `DIAG_SECUN`.

A partir deste patch, a coleta gera:

- `mindlink_internacoes_sp.parquet`
- `mindlink_internacoes_sp.csv`
- `comparativo_filtro_demencia.csv`
- `historico_indicadores.csv`
- `comorbidades.csv`
- `territorio_scores.csv`
- `capacidade_cnes_sp.csv`, quando o CNES rodar

## Como rodar em modo teste

```bash
pip install -r requirements.txt
python 01_coleta_pysus.py
python 04_coleta_cnes.py
python 02_modelo_preditivo.py
python 03_ingestao_oracle.py
```

## Como rodar recorte maior para entrega

```bash
# Linux/macOS
export MINDLINK_ANOS=2020,2021,2022,2023,2024,2025
export MINDLINK_MESES=1,2,3,4,5,6,7,8,9,10,11,12
python 01_coleta_pysus.py

# Windows PowerShell
$env:MINDLINK_ANOS="2020,2021,2022,2023,2024,2025"
$env:MINDLINK_MESES="1,2,3,4,5,6,7,8,9,10,11,12"
python 01_coleta_pysus.py
```

## Entregas que este patch ajuda

| Bloco | Arquivos principais | Matéria |
|---|---|---|
| PySUS real | `01_coleta_pysus.py`, `04_coleta_cnes.py` | Patrícia, Nemec, Rita |
| Modelo analítico | `02_modelo_preditivo.py` | Nemec |
| Oracle | `03_ingestao_oracle.py`, `sql/01_ddl_mindlink_dimensional.sql` | Rita, Data Architecture |
| Select AI | `sql/02_comments_mindlink.sql`, `sql/03_select_ai_perguntas.sql` | Rita, Oracle/Data Architecture |
| Airflow | `dags/mindlink_pipeline_dag.py` | Milton |
| Governança | logs, prints, CSVs tratados e este documento | Selas + todas |

## Observação importante

A taxa de projeção nacional ainda aparece como premissa simplificada. Ela deve ser documentada como premissa auditável e recalibrada depois com população 60+ do recorte escolhido. Isso evita vender certeza onde ainda existe hipótese.
