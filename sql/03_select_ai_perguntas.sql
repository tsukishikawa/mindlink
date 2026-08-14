/*
MindLink — Perguntas estratégicas para Select AI / SQL AI
Use estas perguntas como evidência: prompt → SQL gerado → resultado → insight → recomendação.
*/

-- 1) Crescimento e método de filtro
SELECT DBMS_CLOUD_AI.GENERATE(
  prompt => 'Compare a quantidade de internações capturadas por DIAG_PRINC versus DIAG_PRINC mais DIAG_SECUN. Qual filtro revela maior pressão por demência?',
  profile_name => 'MINDLINK_GEMINI',
  action => 'showsql'
) AS sql_gerado
FROM dual;

-- 2) Permanência média
SELECT DBMS_CLOUD_AI.GENERATE(
  prompt => 'Quais grupos CID de demência apresentam maior permanência média hospitalar?',
  profile_name => 'MINDLINK_GEMINI',
  action => 'showsql'
) AS sql_gerado
FROM dual;

-- 3) Pressão assistencial
SELECT DBMS_CLOUD_AI.GENERATE(
  prompt => 'Quais municípios apresentam maior pressão assistencial considerando internações e leitos SUS?',
  profile_name => 'MINDLINK_GEMINI',
  action => 'showsql'
) AS sql_gerado
FROM dual;

-- 4) Comorbidades invisíveis
SELECT DBMS_CLOUD_AI.GENERATE(
  prompt => 'Quais causas principais aparecem com mais frequência quando a demência está registrada como diagnóstico secundário?',
  profile_name => 'MINDLINK_GEMINI',
  action => 'showsql'
) AS sql_gerado
FROM dual;

-- 5) Projeção executiva
SELECT DBMS_CLOUD_AI.GENERATE(
  prompt => 'Qual é a projeção de internações por demência em 2050 comparada a 2020 e qual recomendação isso gera para uma Secretaria de Saúde?',
  profile_name => 'MINDLINK_GEMINI',
  action => 'narrate'
) AS resposta
FROM dual;
