-- Monthly expense report artifacts + once-per-conversation tips (feature 022)

CREATE TABLE IF NOT EXISTS monthly_report_artifacts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_type text NOT NULL,
    tenant_id text NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    status text NOT NULL
        CHECK (status IN ('preparing', 'ready', 'failed')),
    data_fingerprint text NOT NULL DEFAULT '',
    style_fingerprint text NOT NULL DEFAULT '',
    storage_path text NULL,
    insight_text text NULL,
    snapshot_json jsonb NULL,
    error_code text NULL,
    prepared_at timestamptz NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_type, tenant_id, period_start)
);

CREATE INDEX IF NOT EXISTS monthly_report_artifacts_tenant_status_idx
    ON monthly_report_artifacts (tenant_type, tenant_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS monthly_report_tips (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_type text NOT NULL,
    tenant_id text NOT NULL,
    tip_period_start date NOT NULL,
    shown_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_type, tenant_id, tip_period_start)
);

ALTER TABLE monthly_report_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_report_tips ENABLE ROW LEVEL SECURITY;

-- Bot uses service_role only (no authenticated policies for v1)
GRANT ALL ON monthly_report_artifacts TO service_role;
GRANT ALL ON monthly_report_tips TO service_role;
REVOKE ALL ON monthly_report_artifacts FROM anon, authenticated;
REVOKE ALL ON monthly_report_tips FROM anon, authenticated;

-- Private storage bucket for PNG report images
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'monthly-reports',
    'monthly-reports',
    false,
    5242880,
    ARRAY['image/png']::text[]
)
ON CONFLICT (id) DO NOTHING;
