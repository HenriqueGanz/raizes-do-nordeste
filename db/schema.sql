CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE formato_operacao   AS ENUM ('COMPLETA', 'REDUZIDA');
CREATE TYPE canal_pedido       AS ENUM ('APP', 'TOTEM', 'BALCAO', 'PICKUP');
CREATE TYPE status_pedido      AS ENUM (
    'CRIADO', 'AGUARDANDO_PAGAMENTO', 'PAGO', 'PAGAMENTO_RECUSADO',
    'EM_PREPARO', 'PRONTO', 'ENTREGUE', 'CANCELADO'
);
CREATE TYPE status_pagamento   AS ENUM ('PENDENTE', 'PAGO', 'RECUSADO', 'ESTORNADO');
CREATE TYPE status_consentimento AS ENUM ('CONCEDIDO', 'REVOGADO');
CREATE TYPE papel_usuario       AS ENUM ('CLIENTE', 'OPERADOR', 'ADMIN');

CREATE TABLE unidade (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome             VARCHAR(120) NOT NULL,
    regiao           VARCHAR(60)  NOT NULL,
    cidade           VARCHAR(80)  NOT NULL,
    formato_operacao formato_operacao NOT NULL DEFAULT 'COMPLETA',
    ativa            BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE produto (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        VARCHAR(150) NOT NULL,
    preco_base  NUMERIC(10,2) NOT NULL CHECK (preco_base >= 0),
    categoria   VARCHAR(60)  NOT NULL,
    sazonal     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE disponibilidade_produto (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unidade_id       UUID NOT NULL REFERENCES unidade(id) ON DELETE CASCADE,
    produto_id       UUID NOT NULL REFERENCES produto(id) ON DELETE CASCADE,
    preco_local      NUMERIC(10,2) CHECK (preco_local >= 0),
    disponivel       BOOLEAN NOT NULL DEFAULT TRUE,
    quantidade_estoque INTEGER CHECK (quantidade_estoque >= 0),
    inicio_vigencia  DATE,
    fim_vigencia     DATE,
    UNIQUE (unidade_id, produto_id),
    CHECK (fim_vigencia IS NULL OR inicio_vigencia IS NULL OR fim_vigencia >= inicio_vigencia)
);
CREATE INDEX idx_disp_unidade ON disponibilidade_produto (unidade_id) WHERE disponivel;

CREATE TABLE usuario (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome               VARCHAR(150),
    email              VARCHAR(180) UNIQUE,
    cpf                VARCHAR(11) UNIQUE,
    data_nascimento    DATE,
    pontos_fidelidade  INTEGER NOT NULL DEFAULT 0 CHECK (pontos_fidelidade >= 0),
    papel              papel_usuario NOT NULL DEFAULT 'CLIENTE',
    senha_hash         VARCHAR(200),
    anonimizado        BOOLEAN NOT NULL DEFAULT FALSE,
    anonymized_at      TIMESTAMPTZ,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE consentimento (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id    UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    finalidade    VARCHAR(80) NOT NULL,
    base_legal    VARCHAR(60) NOT NULL,
    status        status_consentimento NOT NULL DEFAULT 'CONCEDIDO',
    versao_termo  VARCHAR(20),
    canal_coleta  canal_pedido,
    concedido_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    revogado_em   TIMESTAMPTZ
);
CREATE INDEX idx_consent_usuario ON consentimento (usuario_id, finalidade);

CREATE TABLE resgate_pontos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    pontos      INTEGER NOT NULL CHECK (pontos > 0),
    cupom       VARCHAR(40) NOT NULL,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_resgate_usuario ON resgate_pontos (usuario_id);

CREATE TABLE pedido (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unidade_id   UUID NOT NULL REFERENCES unidade(id),
    usuario_id   UUID REFERENCES usuario(id),
    canal        canal_pedido NOT NULL,
    status       status_pedido NOT NULL DEFAULT 'CRIADO',
    valor_total  NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (valor_total >= 0),
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_pedido_unidade_status ON pedido (unidade_id, status);

CREATE TABLE item_pedido (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id      UUID NOT NULL REFERENCES pedido(id) ON DELETE CASCADE,
    produto_id     UUID NOT NULL REFERENCES produto(id),
    quantidade     INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(10,2) NOT NULL CHECK (preco_unitario >= 0)
);
CREATE INDEX idx_item_pedido ON item_pedido (pedido_id);

CREATE TABLE pagamento (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pedido_id            UUID NOT NULL UNIQUE REFERENCES pedido(id) ON DELETE CASCADE,
    metodo               VARCHAR(30) NOT NULL,
    valor                NUMERIC(10,2) NOT NULL CHECK (valor >= 0),
    status               status_pagamento NOT NULL DEFAULT 'PENDENTE',
    id_transacao_externa VARCHAR(100),
    idempotency_key      VARCHAR(120) UNIQUE, 
    atualizado_em        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ator_id     UUID,
    pedido_id   UUID REFERENCES pedido(id) ON DELETE SET NULL,
    acao        VARCHAR(60) NOT NULL,
    entidade    VARCHAR(60) NOT NULL,
    detalhes    JSONB,
    ocorrido_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_acao ON audit_log (acao, ocorrido_em);
