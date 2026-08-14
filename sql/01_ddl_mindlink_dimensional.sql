/*
Grupo: She Leads
Projeto: MindLink — Sprint 3
Integrantes:
572387 — Ana Júlia Amorim
572886 — Mariana Ishikawa
569873 — Beatriz Dias da Silva
570351 — Luana Ramos Rabelo
568651 — Sthefany Feitosa da Silva

Fontes: DATASUS/SIH-SUS via PySUS, CNES via PySUS, IBGE/projeções populacionais.
Objetivo: modelo relacional/dimensional para evidenciar PK, FK, relacionamentos,
normalização e suporte ao Select AI.
*/

-- DROP TABLE fato_capacidade_mensal;
-- DROP TABLE fato_internacao_mensal;
-- DROP TABLE dim_estabelecimento;
-- DROP TABLE dim_faixa_etaria;
-- DROP TABLE dim_diagnostico;
-- DROP TABLE dim_municipio;
-- DROP TABLE dim_tempo;

CREATE TABLE dim_tempo (
    id_tempo NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ano NUMBER(4) NOT NULL,
    mes NUMBER(2) NOT NULL,
    trimestre NUMBER(1),
    ano_mes VARCHAR2(7),
    CONSTRAINT uk_dim_tempo UNIQUE (ano, mes)
);

CREATE TABLE dim_municipio (
    id_municipio NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_municipio VARCHAR2(10) NOT NULL,
    nome_municipio VARCHAR2(120),
    uf CHAR(2) NOT NULL,
    regiao VARCHAR2(50),
    CONSTRAINT uk_dim_municipio UNIQUE (codigo_municipio)
);

CREATE TABLE dim_diagnostico (
    id_diagnostico NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cid10 VARCHAR2(10) NOT NULL,
    grupo_diagnostico VARCHAR2(120),
    descricao VARCHAR2(255),
    flag_demencia NUMBER(1) DEFAULT 0,
    CONSTRAINT uk_dim_diagnostico UNIQUE (cid10)
);

CREATE TABLE dim_faixa_etaria (
    id_faixa_etaria NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    faixa_etaria VARCHAR2(20) NOT NULL,
    idade_min NUMBER(3),
    idade_max NUMBER(3),
    CONSTRAINT uk_dim_faixa UNIQUE (faixa_etaria)
);

CREATE TABLE dim_estabelecimento (
    id_estabelecimento NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_cnes VARCHAR2(20) NOT NULL,
    nome_estabelecimento VARCHAR2(200),
    tipo_unidade VARCHAR2(120),
    id_municipio NUMBER,
    CONSTRAINT uk_dim_estabelecimento UNIQUE (codigo_cnes),
    CONSTRAINT fk_estab_municipio FOREIGN KEY (id_municipio)
        REFERENCES dim_municipio (id_municipio)
);

CREATE TABLE fato_internacao_mensal (
    id_fato NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tempo NUMBER NOT NULL,
    id_municipio_residencia NUMBER NOT NULL,
    id_municipio_internacao NUMBER,
    id_diagnostico NUMBER NOT NULL,
    id_faixa_etaria NUMBER,
    id_estabelecimento NUMBER,
    demencia_em VARCHAR2(30),
    quantidade_internacoes NUMBER(12),
    valor_total NUMBER(15,2),
    valor_medio NUMBER(15,2),
    dias_permanencia_total NUMBER(12,2),
    permanencia_media NUMBER(8,2),
    quantidade_obitos NUMBER(12),
    taxa_letalidade NUMBER(8,2),
    CONSTRAINT fk_fato_tempo FOREIGN KEY (id_tempo)
        REFERENCES dim_tempo (id_tempo),
    CONSTRAINT fk_fato_municipio_res FOREIGN KEY (id_municipio_residencia)
        REFERENCES dim_municipio (id_municipio),
    CONSTRAINT fk_fato_municipio_int FOREIGN KEY (id_municipio_internacao)
        REFERENCES dim_municipio (id_municipio),
    CONSTRAINT fk_fato_diagnostico FOREIGN KEY (id_diagnostico)
        REFERENCES dim_diagnostico (id_diagnostico),
    CONSTRAINT fk_fato_faixa FOREIGN KEY (id_faixa_etaria)
        REFERENCES dim_faixa_etaria (id_faixa_etaria),
    CONSTRAINT fk_fato_estabelecimento FOREIGN KEY (id_estabelecimento)
        REFERENCES dim_estabelecimento (id_estabelecimento)
);

CREATE TABLE fato_capacidade_mensal (
    id_capacidade NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tempo NUMBER NOT NULL,
    id_municipio NUMBER NOT NULL,
    id_estabelecimento NUMBER,
    leitos_existentes NUMBER(12),
    leitos_sus NUMBER(12),
    uti_existente NUMBER(12),
    uti_sus NUMBER(12),
    CONSTRAINT fk_capacidade_tempo FOREIGN KEY (id_tempo)
        REFERENCES dim_tempo (id_tempo),
    CONSTRAINT fk_capacidade_municipio FOREIGN KEY (id_municipio)
        REFERENCES dim_municipio (id_municipio),
    CONSTRAINT fk_capacidade_estab FOREIGN KEY (id_estabelecimento)
        REFERENCES dim_estabelecimento (id_estabelecimento)
);
