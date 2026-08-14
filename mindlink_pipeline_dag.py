"""
DAG Airflow — MindLink Sprint 3

Representa o pipeline operacional exigido em Modern Data Architecture & Engineering:
    ingestão → transformação/modelagem → validação → carga analítica

Uso esperado:
    Copiar este arquivo para a pasta dags/ do Airflow.
    Ajustar o caminho BASE_DIR para a raiz do repositório MindLink.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

BASE_DIR = Path.home() / "mindlink"  # ajuste se o repositório estiver em outro caminho
PYTHON = "python"

DEFAULT_ARGS = {
    "owner": "she-leads",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="mindlink_sprint3_pipeline",
    description="Pipeline MindLink: PySUS/SIH + CNES → tratamento → Oracle → evidências",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 8, 1),
    schedule=None,
    catchup=False,
    tags=["mindlink", "sprint3", "pysus", "oracle"],
) as dag:
    inicio = EmptyOperator(task_id="inicio")

    coletar_sih = BashOperator(
        task_id="ingestao_sih_pysus",
        bash_command=f"cd {BASE_DIR} && {PYTHON} 01_coleta_pysus.py",
    )

    coletar_cnes = BashOperator(
        task_id="ingestao_cnes_pysus",
        bash_command=f"cd {BASE_DIR} && {PYTHON} 04_coleta_cnes.py",
    )

    transformar_modelar = BashOperator(
        task_id="transformacao_e_modelo_preditivo",
        bash_command=f"cd {BASE_DIR} && {PYTHON} 02_modelo_preditivo.py",
    )

    validar_arquivos = BashOperator(
        task_id="validacao_arquivos_gerados",
        bash_command=(
            f"cd {BASE_DIR} && "
            "test -f data/processed/mindlink_internacoes_sp.parquet && "
            "test -f data/processed/historico_indicadores.csv && "
            "test -f data/processed/projecao_demencia_2050.csv && "
            "test -f data/processed/comparativo_filtro_demencia.csv"
        ),
    )

    carregar_oracle = BashOperator(
        task_id="carga_analitica_oracle",
        bash_command=f"cd {BASE_DIR} && {PYTHON} 03_ingestao_oracle.py",
    )

    fim = EmptyOperator(task_id="fim")

    inicio >> [coletar_sih, coletar_cnes] >> transformar_modelar >> validar_arquivos >> carregar_oracle >> fim
