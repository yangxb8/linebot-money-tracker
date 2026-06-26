-- Tenant category merchant memory (feature 013)
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

CREATE TABLE IF NOT EXISTS category_merchant_memory (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_type text NOT NULL CHECK (tenant_type IN ('user', 'group', 'room')),
    tenant_id text NOT NULL,
    merchant_key text NOT NULL,
    display_merchant text,
    category_code text NOT NULL,
    weight numeric(6, 2) NOT NULL DEFAULT 0 CHECK (weight >= 0),
    hit_count int NOT NULL DEFAULT 0,
    last_source text NOT NULL CHECK (
        last_source IN ('llm', 'user_correction', 'silent_confirm', 'backfill')
    ),
    last_corrected_by text,
    sample_description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_type, tenant_id, merchant_key)
);

CREATE INDEX IF NOT EXISTS idx_category_merchant_memory_lookup
    ON category_merchant_memory (tenant_type, tenant_id, merchant_key);

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS category_guess_code text,
    ADD COLUMN IF NOT EXISTS category_source text
        CHECK (category_source IS NULL OR category_source IN ('memory', 'llm'));

CREATE OR REPLACE FUNCTION get_category_accuracy_stats(
    p_tenant_type text,
    p_tenant_id text,
    p_days int DEFAULT 30
)
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
    WITH scoped AS (
        SELECT
            e.category_guess_code,
            e.category_node_id,
            cn.code AS final_code
        FROM expenses e
        JOIN category_nodes cn ON cn.id = e.category_node_id
        WHERE e.tenant_type = p_tenant_type
          AND e.tenant_id = p_tenant_id
          AND e.deleted_at IS NULL
          AND e.category_guess_code IS NOT NULL
          AND e.expense_date >= (CURRENT_DATE - GREATEST(p_days, 1))
    ),
    totals AS (
        SELECT
            COUNT(*)::int AS total_expenses,
            COUNT(*) FILTER (WHERE category_guess_code = 'unknown')::int AS unknown_count,
            COUNT(*) FILTER (
                WHERE category_guess_code = final_code
            )::int AS unchanged_count
        FROM scoped
    )
    SELECT jsonb_build_object(
        'total_expenses', total_expenses,
        'pct_guess_unknown', CASE
            WHEN total_expenses = 0 THEN 0
            ELSE ROUND(unknown_count::numeric / total_expenses, 4)
        END,
        'pct_guess_unchanged', CASE
            WHEN total_expenses = 0 THEN 0
            ELSE ROUND(unchanged_count::numeric / total_expenses, 4)
        END
    )
    FROM totals;
$$;

GRANT EXECUTE ON FUNCTION get_category_accuracy_stats(text, text, int) TO service_role;
