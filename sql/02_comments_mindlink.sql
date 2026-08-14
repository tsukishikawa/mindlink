/*
MindLink — Comentários semânticos para Oracle Select AI
Objetivo: deixar o modelo legível para gestores e orientar a geração de SQL.
*/

COMMENT ON TABLE dim_tempo IS 'Dimensão temporal usada para análises mensais, anuais, trimestrais e comparativos históricos de internações por demência.';
COMMENT ON COLUMN dim_tempo.ano IS 'Ano de competência do registro de internação ou capacidade hospitalar.';
COMMENT ON COLUMN dim_tempo.mes IS 'Mês de competência do registro de internação ou capacidade hospitalar.';

COMMENT ON TABLE dim_municipio IS 'Dimensão territorial com município, UF e região, permitindo filtros territoriais e comparação entre localidades.';
COMMENT ON COLUMN dim_municipio.codigo_municipio IS 'Código do município conforme padrão utilizado nas bases públicas de saúde.';
COMMENT ON COLUMN dim_municipio.uf IS 'Unidade federativa do município.';

COMMENT ON TABLE dim_diagnostico IS 'Dimensão clínica com códigos CID-10, incluindo demências F00, F01, F02, F03 e doença de Alzheimer G30.';
COMMENT ON COLUMN dim_diagnostico.flag_demencia IS 'Indica se o CID pertence ao recorte clínico de demência da MindLink.';

COMMENT ON TABLE dim_faixa_etaria IS 'Dimensão de perfil etário usada para análise de envelhecimento e pressão assistencial por idade.';

COMMENT ON TABLE dim_estabelecimento IS 'Dimensão de estabelecimentos de saúde, vinculada ao CNES e ao município de atendimento.';
COMMENT ON COLUMN dim_estabelecimento.codigo_cnes IS 'Código CNES do estabelecimento de saúde.';

COMMENT ON TABLE fato_internacao_mensal IS 'Tabela fato com indicadores mensais de internações hospitalares associadas à demência, por tempo, território, diagnóstico, faixa etária e estabelecimento.';
COMMENT ON COLUMN fato_internacao_mensal.demencia_em IS 'Informa se a demência foi detectada como diagnóstico principal, secundário ou ambos.';
COMMENT ON COLUMN fato_internacao_mensal.quantidade_internacoes IS 'Quantidade de internações no recorte analisado.';
COMMENT ON COLUMN fato_internacao_mensal.permanencia_media IS 'Média de dias de permanência hospitalar.';
COMMENT ON COLUMN fato_internacao_mensal.taxa_letalidade IS 'Percentual de internações que resultaram em óbito no recorte analisado.';

COMMENT ON TABLE fato_capacidade_mensal IS 'Tabela fato com capacidade hospitalar mensal obtida do CNES, incluindo leitos existentes, leitos SUS e UTI.';
COMMENT ON COLUMN fato_capacidade_mensal.leitos_sus IS 'Quantidade de leitos disponíveis ao SUS no município ou estabelecimento.';
COMMENT ON COLUMN fato_capacidade_mensal.uti_sus IS 'Quantidade de leitos de UTI disponíveis ao SUS.';
