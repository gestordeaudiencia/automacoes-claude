-- =================================================================
-- automacoes-claude — schema base (multi-plataforma)
-- Idempotente: pode rodar várias vezes sem quebrar.
-- =================================================================

-- Eventos de qualquer plataforma de pagamento (Kiwify, Hotmart, Shopify, ...)
CREATE TABLE IF NOT EXISTS eventos_pagamento (
    id BIGSERIAL PRIMARY KEY,
    platform TEXT NOT NULL,             -- 'kiwify' | 'hotmart' | 'shopify' | ...
    raw_event_type TEXT NOT NULL,       -- evento nativo da plataforma
    event_kind TEXT NOT NULL,           -- 'pix' | 'boleto' | 'compra_aprovada' | ...
    user_number TEXT,
    email TEXT,
    customer_name TEXT,
    product_name TEXT,
    product_id TEXT,
    charge_amount BIGINT,               -- em centavos
    pix_code TEXT,
    pix_expiration TEXT,
    boleto_url TEXT,
    boleto_barcode TEXT,
    boleto_expiry TEXT,
    access_url TEXT,
    rejection_reason TEXT,
    payment_method TEXT,
    raw_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eventos_user_created ON eventos_pagamento(user_number, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_eventos_kind ON eventos_pagamento(event_kind);
CREATE INDEX IF NOT EXISTS idx_eventos_platform ON eventos_pagamento(platform);

-- Estado do contato
CREATE TABLE IF NOT EXISTS contatos_agente (
    user_number TEXT PRIMARY KEY,
    email TEXT,
    nome TEXT,
    agente TEXT NOT NULL DEFAULT 'on',          -- 'on' = bot, 'off' = humano assumiu
    produto_interesse TEXT,
    link_oferta TEXT,
    platform_origem TEXT,                       -- de onde veio o lead
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contatos_agente ON contatos_agente(agente);

-- Follow-ups disparados (idempotência + log)
CREATE TABLE IF NOT EXISTS follow_up (
    id BIGSERIAL PRIMARY KEY,
    user_number TEXT NOT NULL,
    tipo TEXT NOT NULL,
    produto TEXT,
    status TEXT NOT NULL DEFAULT 'completed',
    etapa_atual INT DEFAULT 1,
    scheduled_at TIMESTAMPTZ,
    message TEXT,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_followup_user_tipo ON follow_up(user_number, tipo, created_at DESC);

-- Memória LLM por sessão de WhatsApp
CREATE TABLE IF NOT EXISTS chat_histories (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    message JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_session_created ON chat_histories(session_id, created_at DESC);

-- updated_at trigger
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_contatos_updated_at ON contatos_agente;
CREATE TRIGGER trg_contatos_updated_at
    BEFORE UPDATE ON contatos_agente
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
