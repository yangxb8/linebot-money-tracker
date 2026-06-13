-- Per-user LLM usage limits (feature 007)

CREATE TABLE IF NOT EXISTS user_usage_summary (
    line_user_id text NOT NULL,
    jst_year_month text NOT NULL,
    tier text NOT NULL DEFAULT 'free',
    lifetime_invocations bigint NOT NULL DEFAULT 0,
    month_invocations int NOT NULL DEFAULT 0,
    month_receipt_analyses int NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (line_user_id, jst_year_month)
);

CREATE INDEX IF NOT EXISTS idx_user_usage_summary_user
    ON user_usage_summary (line_user_id);

CREATE TABLE IF NOT EXISTS llm_usage_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    charged_line_user_id text NOT NULL,
    sender_line_user_id text NOT NULL,
    operation_type text NOT NULL,
    operation_label text NOT NULL,
    source_message_id text,
    tenant_type text,
    tenant_id text,
    pooled boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_usage_events_idempotent
    ON llm_usage_events (source_message_id, operation_label)
    WHERE source_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_llm_usage_events_charged_created
    ON llm_usage_events (charged_line_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS llm_message_windows (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_line_user_id text NOT NULL,
    source_message_id text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_llm_message_windows_sender_created
    ON llm_message_windows (sender_line_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tenant_chat_members (
    tenant_type text NOT NULL,
    tenant_id text NOT NULL,
    line_user_id text NOT NULL,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_type, tenant_id, line_user_id)
);
