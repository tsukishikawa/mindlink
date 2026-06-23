-- ✅ CONFIGURAÇÃO QUE FUNCIONOU (Free Tier / região SP):
--    Provider Google Gemini, modelo gemini-2.5-flash, profile MINDLINK_GEMINI.
--    Crie o profile com nome NOVO para não herdar versões antigas, e rode as
--    perguntas com o cursor na linha + Ctrl+Enter (nunca o play geral).
--    SELECT DBMS_CLOUD_AI.GENERATE(prompt=>'...', profile_name=>'MINDLINK_GEMINI',
--                                  action=>'showsql'|'narrate'|'runsql') FROM dual;

-- ═══════════════════════════════════════════════════════════════════
--  MindLink — Select AI no Oracle Autonomous Database
--  Demência F00-F03 + G30 · base SP-município → projeção Brasil 2020-2050
--  Equipe She Leads · Oracle Challenge FIAP 2026
--
--  ONDE RODAR: Database Actions → SQL (web). Rode bloco a bloco.
--  ⚠ No SQL Worksheet web o atalho "SELECT AI ..." NÃO funciona —
--    use DBMS_CLOUD_AI.GENERATE (passo 5A). O "SELECT AI" puro só
--    funciona no SQLcl / SQL*Plus (passo 5B).
-- ═══════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════
-- ⭐ ATALHO GRATUITO — GOOGLE GEMINI (recomendado para Free Tier / SP)
--    Funciona em qualquer região: é chamada HTTPS externa, sem dynamic
--    group, sem policy, sem GenAI da OCI. Chave grátis em aistudio.google.com
--    (Get API key → Create API key, começa com AIza...). Rode os 4 blocos:
-- ═══════════════════════════════════════════════════════════════════
-- BEGIN
--   DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
--     host => 'generativelanguage.googleapis.com',
--     ace  => xs$ace_type(privilege_list => xs$name_list('http'),
--                         principal_name => 'ADMIN', principal_type => xs_acl.ptype_db));
-- END;
-- /
-- BEGIN
--   DBMS_CLOUD.CREATE_CREDENTIAL(credential_name => 'GOOGLE_CRED',
--                                username => 'GOOGLE', password => 'AIza_sua_chave');
-- END;
-- /
-- BEGIN DBMS_CLOUD_AI.DROP_PROFILE('MINDLINK_GEMINI', force => TRUE); END;
-- /
-- BEGIN
--   DBMS_CLOUD_AI.CREATE_PROFILE(profile_name => 'MINDLINK_GEMINI',
--     attributes => '{"provider":"google","credential_name":"GOOGLE_CRED",
--       "model":"gemini-2.5-flash","comments":"true",
--       "object_list":[
--         {"owner":"ADMIN","name":"MINDLINK_INTERNACOES"},
--         {"owner":"ADMIN","name":"MINDLINK_INDICADORES"},
--         {"owner":"ADMIN","name":"MINDLINK_PROJECAO"},
--         {"owner":"ADMIN","name":"MINDLINK_TERRITORIO"},
--         {"owner":"ADMIN","name":"MINDLINK_COMORBIDADES"}]}');
-- END;
-- /
-- EXEC DBMS_CLOUD_AI.SET_PROFILE('MINDLINK_GEMINI');
-- (se "model not found", troque por gemini-3.5-flash ou gemini-flash-latest)
-- Depois pule direto para o passo 5A (perguntas). Os passos 1-4 abaixo
-- são as outras opções (OCI / OpenAI) — só use se NÃO usar o Gemini.

-- 0. PRIVILÉGIO (o ADMIN já tem; só precisa se usar outro usuário)
-- GRANT EXECUTE ON DBMS_CLOUD_AI TO SEU_USUARIO;

-- ───────────────────────────────────────────────────────────────────
-- 1. CREDENCIAL DO PROVEDOR DE IA  — escolha UMA das opções
-- ───────────────────────────────────────────────────────────────────

-- OPÇÃO A (recomendada): OCI Generative AI via "resource principal"
--   Sem API key externa. O BANCO age como principal — então a policy aponta
--   para um DYNAMIC GROUP (não para o seu grupo de usuário). No console OCI:
--     1) Identity & Security → Dynamic Groups → Create
--        regra:  resource.id = 'ocid1.autonomousdatabase.oc1....'  (OCID do seu ADB)
--     2) Identity & Security → Policies → Create
--        allow dynamic-group <nome-do-dg> to manage generative-ai-family in compartment <compartment>
--        (se a tenancy usa Identity Domains:  ...dynamic-group '<dominio>/<nome-do-dg>'...)
--   Confirme que a sua REGIÃO tem OCI Generative AI e ajuste "region" no profile (passo 2A).
BEGIN
  DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI', username => 'ADMIN');
END;
/
-- (a credencial interna passa a se chamar OCI$RESOURCE_PRINCIPAL — usada no passo 2A)

-- OPÇÃO B: OpenAI (mais simples para protótipo; precisa de chave sk-... com crédito)
--   1) libere o acesso de rede ao endpoint da OpenAI:
-- BEGIN
--   DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
--     host => 'api.openai.com',
--     ace  => xs$ace_type(privilege_list => xs$name_list('http'),
--                         principal_name => 'ADMIN', principal_type => xs_acl.ptype_db));
-- END;
-- /
--   2) crie a credencial com a chave:
-- BEGIN
--   DBMS_CLOUD.CREATE_CREDENTIAL(credential_name => 'MINDLINK_AI_CRED',
--                                username => 'OPENAI', password => 'sk-sua_chave');
-- END;
-- /

-- ───────────────────────────────────────────────────────────────────
-- 2. PERFIL SELECT AI  — escolha o que combina com a credencial acima
-- ───────────────────────────────────────────────────────────────────
BEGIN
  DBMS_CLOUD_AI.DROP_PROFILE(profile_name => 'MINDLINK_GEMINI', force => TRUE);
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- 2A. Perfil OCI Generative AI (combina com a OPÇÃO A)
--   ⚠ REGIÃO: o OCI Generative AI NÃO existe em sa-saopaulo-1. Aponte para uma
--      região que tenha o serviço (us-chicago-1 é a principal). A chamada cruza
--      de região sem problema porque a policy é no nível da tenancy.
--   Sem "model" → o OCI usa o modelo padrão da região (menos chance de erro).
BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => 'MINDLINK_GEMINI',
    attributes   => '{
      "provider":"oci",
      "credential_name":"OCI$RESOURCE_PRINCIPAL",
      "region":"us-chicago-1",
      "comments":"true",
      "object_list":[
        {"owner":"ADMIN","name":"MINDLINK_INTERNACOES"},
        {"owner":"ADMIN","name":"MINDLINK_INDICADORES"},
        {"owner":"ADMIN","name":"MINDLINK_PROJECAO"},
        {"owner":"ADMIN","name":"MINDLINK_TERRITORIO"},
        {"owner":"ADMIN","name":"MINDLINK_COMORBIDADES"}
      ]
    }'
  );
END;
/

-- 2B. Perfil OpenAI (combina com a OPÇÃO B) — descomente se usar OpenAI
-- BEGIN
--   DBMS_CLOUD_AI.CREATE_PROFILE(
--     profile_name => 'MINDLINK_GEMINI',
--     attributes   => '{
--       "provider":"openai", "credential_name":"MINDLINK_AI_CRED",
--       "model":"gpt-4o-mini", "comments":"true",
--       "object_list":[
--         {"owner":"ADMIN","name":"MINDLINK_INTERNACOES"},
--         {"owner":"ADMIN","name":"MINDLINK_INDICADORES"},
--         {"owner":"ADMIN","name":"MINDLINK_PROJECAO"},
--         {"owner":"ADMIN","name":"MINDLINK_TERRITORIO"},
--         {"owner":"ADMIN","name":"MINDLINK_COMORBIDADES"}]}'
--   );
-- END;
-- /

-- ───────────────────────────────────────────────────────────────────
-- 3. COMENTÁRIOS (contexto para o LLM — "comments":"true" os lê)
-- ───────────────────────────────────────────────────────────────────
COMMENT ON TABLE MINDLINK_INTERNACOES IS
'Internações por demência (CID-10 F00-F03 + G30) no SUS, base observada em São Paulo-município, 2020-2025. Fonte: SIH-SUS/DATASUS via PySUS.';
COMMENT ON COLUMN MINDLINK_INTERNACOES.cid_grupo IS
'Grupo CID-10: F00 e G30=Alzheimer, F01=Demência Vascular, F02=outras doenças, F03=não especificada.';
COMMENT ON COLUMN MINDLINK_INTERNACOES.valor_total IS 'Valor pago pelo SUS pela internação, em reais.';
COMMENT ON COLUMN MINDLINK_INTERNACOES.faixa_etaria IS 'Faixa etária: <60, 60-69, 70-74, 75-79, 80-84, 85+.';
COMMENT ON TABLE MINDLINK_PROJECAO IS
'Projeção nacional de internações por demência 2020-2050. Taxa observada em SP-município (24,25 AIH/100 mil hab. 60+) aplicada à projeção populacional 60+ do IBGE. Custo em 3 cenários SIGTAP (A congelada, B parcial, C pleno).';
COMMENT ON COLUMN MINDLINK_PROJECAO.eh_projecao IS '1 = ano projetado, 0 = ano-base/observado.';
COMMENT ON COLUMN MINDLINK_PROJECAO.taxa_por_100k IS 'AIH de demência por 100 mil habitantes 60+.';
COMMENT ON TABLE MINDLINK_TERRITORIO IS
'Ranking territorial de risco por UF (score 0-100) e crescimento projetado de internações por demência.';
COMMENT ON TABLE MINDLINK_COMORBIDADES IS
'Condições associadas quando a demência aparece como diagnóstico SECUNDÁRIO (pneumonia, infecção urinária, fratura de fêmur etc.).';

-- ───────────────────────────────────────────────────────────────────
-- 4. ATIVAR O PERFIL NA SESSÃO (refaça a cada nova sessão)
-- ───────────────────────────────────────────────────────────────────
EXEC DBMS_CLOUD_AI.SET_PROFILE('MINDLINK_GEMINI');

-- ───────────────────────────────────────────────────────────────────
-- 5A. PERGUNTAS no Database Actions SQL (web) → use GENERATE
--     action: 'showsql' (vê o SQL), 'runsql' (executa), 'narrate' (texto), 'chat'
-- ───────────────────────────────────────────────────────────────────
SELECT DBMS_CLOUD_AI.GENERATE(
  prompt => 'Qual a projeção de internações por demência no Brasil em 2050 comparada a 2020?',
  profile_name => 'MINDLINK_GEMINI', action => 'showsql') AS sql_gerado FROM dual;

SELECT DBMS_CLOUD_AI.GENERATE(
  prompt => 'Quais UFs têm maior score de risco territorial para demência?',
  profile_name => 'MINDLINK_GEMINI', action => 'narrate') AS resposta FROM dual;

SELECT DBMS_CLOUD_AI.GENERATE(
  prompt => 'Custo total projetado em 2050: SIGTAP congelada versus reajuste pleno?',
  profile_name => 'MINDLINK_GEMINI', action => 'narrate') AS resposta FROM dual;

-- ───────────────────────────────────────────────────────────────────
-- 5B. Mesmas perguntas no SQLcl / SQL*Plus → atalho SELECT AI
-- ───────────────────────────────────────────────────────────────────
-- SELECT AI Qual a projeção de internações por demência no Brasil em 2050?;
-- SELECT AI showsql Quais UFs têm maior score de risco territorial?;
-- SELECT AI narrate Resuma o impacto do envelhecimento sobre as internações até 2050;