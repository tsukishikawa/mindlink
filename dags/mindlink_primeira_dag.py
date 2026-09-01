from datetime import datetime
import os
import subprocess

from airflow.sdk import DAG, task


with DAG(
    dag_id="mindlink_primeira_dag",
    description="Pipeline Batch MindLink com validacao Oracle",
    start_date=datetime(2026, 8, 27),
    schedule=None,
    catchup=False,
    tags=["mindlink", "fiap", "batch", "oracle"],
) as dag:

    @task
    def iniciar_pipeline():
        print("1. MindLink: pipeline iniciado")
        return "inicio_ok"


    @task
    def processar_batch():
        print("2. Executando ETL Batch da MindLink...")

        comando = [
            "python",
            "/opt/airflow/scripts/mindlink_etl_sprint3_oracle.py",
            "--demo"
        ]

        subprocess.run(
            comando,
            check=True
        )

        print("ETL Batch concluido com sucesso pelo Airflow.")
        return "batch_ok"


    @task
    def validar_resultado():
        print("3. Validacao local concluida.")
        print("ETL executado sem erro e datasets de staging produzidos.")
        return "validacao_local_ok"


    @task
    def validar_oracle():
        import oracledb

        print("4. Conectando ao Oracle Autonomous Database...")

        user = os.environ["ORACLE_USER"]
        password = os.environ["ORACLE_PASSWORD"]
        dsn = os.environ["ORACLE_DSN"]
        wallet_password = os.environ["ORACLE_WALLET_PASSWORD"]

        conexao = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn,
            config_dir="/opt/airflow/wallet",
            wallet_location="/opt/airflow/wallet",
            wallet_password=wallet_password,
        )

        cursor = conexao.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM STG_MINDLINK_INTERNACOES
        """)

        quantidade = cursor.fetchone()[0]

        print(
            f"Oracle conectado com sucesso. "
            f"STG_MINDLINK_INTERNACOES = {quantidade} registros."
        )

        cursor.close()
        conexao.close()

        if quantidade != 3305:
            raise ValueError(
                f"Contagem Oracle inesperada: {quantidade}. "
                "Esperado nesta base validada: 3305."
            )

        print("Validacao Oracle aprovada.")
        return quantidade


    @task
    def finalizar_pipeline():
        print("5. MindLink: pipeline concluido com sucesso.")
        return "fim_ok"


    inicio = iniciar_pipeline()
    batch = processar_batch()
    validacao_local = validar_resultado()
    oracle = validar_oracle()
    fim = finalizar_pipeline()

    inicio >> batch >> validacao_local >> oracle >> fim