# Dados

O repositório não versiona dados brutos, Wallet, credenciais ou resultados regeneráveis.

O ETL cria automaticamente:

- `data/raw/`: amostra da entrada usada no run;
- `data/processed/`: dados tratados e stagings;
- `data/evidence/`: resumos e contagens de validação;
- `data/reference/`: lookups locais de CNES e CID fornecidos pela equipe.

No modo `--demo`, todos os registros são sintéticos e determinísticos.
