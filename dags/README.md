# DAG Airflow

`mindlink_primeira_dag.py` é a DAG registrada nas evidências finais da Sprint 3.

Ela possui cinco tasks:

1. inicia o pipeline;
2. executa o ETL em modo `--demo`;
3. confirma a geração dos resultados locais;
4. conecta ao Oracle e valida a contagem da staging;
5. finaliza o fluxo.

O valor `3.305` é a contagem da base validada naquela entrega. Antes de reutilizar a DAG com outra carga, transforme essa regra em parâmetro de ambiente ou ajuste a expectativa documentadamente.

A DAG espera o ETL em `/opt/airflow/scripts/` e a Wallet em `/opt/airflow/wallet/`. Esses caminhos pertencem ao contêiner utilizado na execução e podem exigir adaptação em outro ambiente.
