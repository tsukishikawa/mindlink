# Como contribuir

O repositório é colaborativo e representa uma entrega acadêmica da equipe She Leads.

## Fluxo recomendado

1. Sincronize sua cópia com a branch principal.
2. Crie uma branch curta, por exemplo `docs/readme-fase-04` ou `fix/validacao-etl`.
3. Faça alterações pequenas e relacionadas entre si.
4. Execute `pytest` antes do commit.
5. Abra um Pull Request explicando o que mudou e qual evidência foi atualizada.

## Regras de integridade

- Não versionar `.env`, Wallet, senha, token, chave de API ou base bruta.
- Não apresentar dado sintético como resultado do SUS.
- Diferenciar claramente `implementado`, `executado`, `evidenciado` e `planejado`.
- Não alterar o grão Oracle sem atualizar ETL, DDL, DML, testes e documentação.
- Não chamar cadastro de leitos de disponibilidade em tempo real.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Testes que dependem do Oracle devem ser registrados separadamente e nunca incorporar credenciais ao código.
