# MindLink Sprint 3 — Patch PySUS + Oracle

Este pacote contém arquivos para substituir/adicionar no repositório `tsukishikawa/mindlink`.

## Substituir arquivos existentes

- `01_coleta_pysus.py`
- `02_modelo_preditivo.py`
- `03_ingestao_oracle.py`

## Adicionar arquivos novos

- `04_coleta_cnes.py`
- `dags/mindlink_pipeline_dag.py`
- `sql/01_ddl_mindlink_dimensional.sql`
- `sql/02_comments_mindlink.sql`
- `sql/03_select_ai_perguntas.sql`
- `docs/Sprint3_Ajustes_Arquitetura.md`

## Mudança principal

Antes:

```text
CSV/projeção ou DIAG_PRINC isolado
```

Agora:

```text
PySUS/SIH-SUS → DIAG_PRINC + DIAG_SECUN → dados tratados → Oracle → Select AI
```

## Primeira execução recomendada

```bash
python 01_coleta_pysus.py
python 04_coleta_cnes.py
python 02_modelo_preditivo.py
python 03_ingestao_oracle.py
```

## Para a entrega oficial

Depois que o teste rodar, ampliar o período:

```bash
# Windows PowerShell
$env:MINDLINK_ANOS="2020,2021,2022,2023,2024,2025"
$env:MINDLINK_MESES="1,2,3,4,5,6,7,8,9,10,11,12"
python 01_coleta_pysus.py
```

O CSV tratado gerado pelo PySUS pode ser usado na importação via SQL Developer para atender a Rita. Ele não é fonte manual; é produto intermediário rastreável do pipeline.
