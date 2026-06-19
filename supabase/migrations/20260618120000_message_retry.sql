-- Reply-to-bot-error retry (inbound message store + failure anchors)

CREATE TABLE IF NOT EXISTS inbound_messages (
    message_id text PRIMARY KEY,
    line_user_id text NOT NULL,
    tenant_type text NOT NULL,
    tenant_id text NOT NULL,
    message_type text NOT NULL CHECK (message_type IN ('text', 'image')),
    text_content text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_inbound_messages_created_at
    ON inbound_messages (created_at);

CREATE INDEX IF NOT EXISTS idx_inbound_messages_tenant
    ON inbound_messages (tenant_type, tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS failure_retry_anchors (
    bot_error_message_id text PRIMARY KEY,
    original_message_id text NOT NULL REFERENCES inbound_messages (message_id) ON DELETE CASCADE,
    original_line_user_id text NOT NULL,
    tenant_type text NOT NULL,
    tenant_id text NOT NULL,
    failure_kind text NOT NULL CHECK (failure_kind IN ('processing_error', 'image_fetch_error')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_failure_retry_anchors_tenant
    ON failure_retry_anchors (tenant_type, tenant_id, created_at DESC);

ALTER TABLE inbound_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE failure_retry_anchors ENABLE ROW LEVEL SECURITY;
