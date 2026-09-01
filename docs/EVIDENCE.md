# Matriz de evidências técnicas

| Evidência | Arquivo principal | O que prova | O que não prova |
|---|---|---|---|
| ETL Python | `src/mindlink_etl_sprint3_oracle.py` | Extração parametrizada, modo demo, transformação, qualidade e geração das stagings | Disponibilidade contínua do PySUS ou execução Oracle sem credenciais |
| Teste demonstrativo | `tests/test_demo_pipeline.py` | Execução ponta a ponta sem fonte externa | Resultado epidemiológico real |
| DAG Airflow | `dags/mindlink_primeira_dag.py` | Ordem das tasks, execução demo e consulta de validação Oracle | Carga das 3.305 linhas naquele mesmo run |
| Modelo Oracle | `sql/01_ddl_mindlink_sprint3.sql` | Estrutura de staging, dimensões, fatos, constraints, índices e views | Que todos os objetos estejam disponíveis hoje |
| Carga da Sprint 3 | `sql/02_dml_mindlink_sprint3.sql` | Registros e comandos utilizados para popular/promover o modelo da entrega | Atualização automática posterior |
| Análise estatística | `notebooks/EC_Sprint_3_MindLink_SheLeads_ML_FINAL.ipynb` | Exploração, testes estatísticos e discussão metodológica | Modelo preditivo de produção |
| Arquitetura | `docs/ARCHITECTURE.md` | Escolha Lambda e separação entre batch implementado e speed futura | Streaming em tempo real |

## Evidências visuais existentes

Os relatórios acadêmicos da Sprint 3 registram:

- DAG com cinco tasks concluídas;
- log do ETL demonstrativo;
- conexão do Airflow ao Oracle por Wallet;
- consulta de 3.305 registros em `STG_MINDLINK_INTERNACOES`;
- tabelas de staging, dimensões, fatos e views no Oracle Database Actions.

Arquivos de imagem, Wallet, credenciais e bases brutas não são versionados neste repositório. A ausência desses arquivos no GitHub é um controle de segurança, não ausência de documentação.
