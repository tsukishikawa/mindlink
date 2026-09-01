# Status técnico

Este documento separa o que existe no código do que foi executado e do que ainda depende de ambiente externo.

| Item | Código no repositório | Evidência de execução | Dependência externa | Status atual |
|---|---:|---:|---:|---|
| ETL demonstrativo | Sim | Sim | Não | Reproduzível localmente |
| Validações de qualidade | Sim | Sim | Não | Reproduzível localmente |
| Stagings CSV | Sim | Sim | Não | Reproduzível localmente |
| Coleta SIH/SUS via PySUS | Sim | Parcial | PySUS/DATASUS | Não executada no CI |
| Enriquecimento CNES/CID | Sim | Sim na entrega | Arquivos auxiliares | Depende dos arquivos oficiais |
| Modelo dimensional Oracle | Sim | Sim na entrega | Oracle ADB | Sem reexecução nesta revisão |
| DML da carga Oracle | Sim | Sim na entrega | Oracle ADB | Preservada como evidência técnica |
| DAG Airflow | Sim | Sim | Airflow + Wallet | Executada no ambiente da Sprint 3 |
| Validação de 3.305 linhas | Sim | Sim | Oracle ADB | Consulta a staging previamente carregada |
| Select AI | Referências legadas | Parcial | Perfil e credencial de IA | Não reproduzido nesta revisão |
| Dashboard Oracle ao vivo | Não | Não | Backend hospedado | Fora do escopo comprovado |
| Previsão operacional | Estrutura/notebook | Não como produção | Série, modelo e monitoramento | Pesquisa/protótipo |

## Leitura correta da execução Airflow

A DAG `mindlink_primeira_dag` executa o ETL com `--demo`, valida que os arquivos locais foram gerados e, em outra task, conecta ao Oracle para consultar `STG_MINDLINK_INTERNACOES`.

A consulta retornou 3.305 linhas no ambiente utilizado na Sprint 3. O comando chamado pela DAG não contém `--oracle-load`; portanto, a execução comprovou orquestração local e integração de leitura com o Oracle, mas não realizou a carga dessas 3.305 linhas naquele run.

## Próximas validações quando o Oracle estiver disponível

1. Confirmar contagens de staging, dimensões, fatos e views.
2. Comparar as competências existentes com `202401–202512`.
3. Executar consultas de integridade de PK, FK e grão.
4. Verificar COMMENTS semânticos e objetos expostos ao Select AI.
5. Registrar pergunta, SQL gerado e resposta do Select AI sem expor credenciais.
