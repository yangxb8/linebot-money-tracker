-- Per-tenant settings (fiscal month start day for budget periods)

CREATE TABLE IF NOT EXISTS tenant_settings (
    tenant_type text NOT NULL,
    tenant_id text NOT NULL,
    fiscal_start_day smallint NOT NULL DEFAULT 1
        CHECK (fiscal_start_day BETWEEN 1 AND 28),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_type, tenant_id)
);

ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_settings_select
    ON tenant_settings FOR SELECT TO authenticated
    USING (can_access_tenant(tenant_type, tenant_id));

CREATE POLICY tenant_settings_insert
    ON tenant_settings FOR INSERT TO authenticated
    WITH CHECK (can_access_tenant(tenant_type, tenant_id));

CREATE POLICY tenant_settings_update
    ON tenant_settings FOR UPDATE TO authenticated
    USING (can_access_tenant(tenant_type, tenant_id))
    WITH CHECK (can_access_tenant(tenant_type, tenant_id));

GRANT SELECT, INSERT, UPDATE ON tenant_settings TO authenticated;

CREATE OR REPLACE FUNCTION get_tenant_fiscal_start_day(
    p_tenant_type text,
    p_tenant_id text
) RETURNS smallint
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT COALESCE(
        (
            SELECT ts.fiscal_start_day
            FROM tenant_settings ts
            WHERE ts.tenant_type = p_tenant_type
              AND ts.tenant_id = p_tenant_id
        ),
        1::smallint
    );
$$;

GRANT EXECUTE ON FUNCTION get_tenant_fiscal_start_day(text, text) TO authenticated;

-- Fiscal periods use budget_month as the period start date (e.g. 2026-05-25 for a 25th-start month).
CREATE OR REPLACE FUNCTION get_budget_summary(
    p_tenant_type text,
    p_tenant_id text,
    p_budget_month date,
    p_currency char(3) DEFAULT 'JPY'
) RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_today date;
    v_month_start date;
    v_month_end date;
    v_days_in_month int;
    v_elapsed int;
    v_fiscal_start_day smallint;
    v_total_spent numeric;
    v_unbudgeted numeric;
    v_has_any_limit boolean;
    v_total_limit numeric;
    v_budgets jsonb;
    v_spent_by_bucket jsonb;
BEGIN
    IF NOT can_access_tenant(p_tenant_type, p_tenant_id) THEN
        RAISE EXCEPTION 'access denied for tenant %:%', p_tenant_type, p_tenant_id;
    END IF;

    v_fiscal_start_day := get_tenant_fiscal_start_day(p_tenant_type, p_tenant_id);
    v_today := (now() AT TIME ZONE 'Asia/Tokyo')::date;
    v_month_start := p_budget_month;
    v_month_end := (p_budget_month + interval '1 month' - interval '1 day')::date;
    v_days_in_month := (v_month_end - v_month_start) + 1;

    IF v_today < v_month_start THEN
        v_elapsed := 0;
    ELSIF v_today > v_month_end THEN
        v_elapsed := v_days_in_month;
    ELSE
        v_elapsed := GREATEST(1, (v_today - v_month_start) + 1);
    END IF;

    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'budget_level', mb.budget_level,
            'category_node_id', mb.category_node_id,
            'amount', mb.amount
        )
    ), '[]'::jsonb)
    INTO v_budgets
    FROM monthly_budgets mb
    WHERE mb.tenant_type = p_tenant_type
      AND mb.tenant_id = p_tenant_id
      AND mb.budget_month = p_budget_month
      AND mb.currency = p_currency;

    SELECT EXISTS (
        SELECT 1
        FROM monthly_budgets mb
        WHERE mb.tenant_type = p_tenant_type
          AND mb.tenant_id = p_tenant_id
          AND mb.budget_month = p_budget_month
          AND mb.currency = p_currency
    ) INTO v_has_any_limit;

    SELECT COALESCE(SUM(e.amount), 0)
    INTO v_total_spent
    FROM expenses e
    WHERE e.tenant_type = p_tenant_type
      AND e.tenant_id = p_tenant_id
      AND e.currency = p_currency
      AND e.deleted_at IS NULL
      AND e.expense_date >= v_month_start
      AND e.expense_date <= v_month_end;

    SELECT COALESCE(SUM(e.amount), 0)
    INTO v_unbudgeted
    FROM expenses e
    WHERE e.tenant_type = p_tenant_type
      AND e.tenant_id = p_tenant_id
      AND e.currency = p_currency
      AND e.deleted_at IS NULL
      AND e.expense_date >= v_month_start
      AND e.expense_date <= v_month_end
      AND resolve_budget_bucket(
          e.assigned_level,
          e.category_node_id,
          e.category_l1_id,
          p_tenant_type,
          p_tenant_id,
          p_budget_month,
          p_currency
      ) = 'unbudgeted';

    SELECT mb.amount
    INTO v_total_limit
    FROM monthly_budgets mb
    WHERE mb.tenant_type = p_tenant_type
      AND mb.tenant_id = p_tenant_id
      AND mb.budget_month = p_budget_month
      AND mb.currency = p_currency
      AND mb.budget_level = 'total'
    LIMIT 1;

    SELECT COALESCE(jsonb_object_agg(bucket, spent), '{}'::jsonb)
    INTO v_spent_by_bucket
    FROM (
        SELECT
            resolve_budget_bucket(
                e.assigned_level,
                e.category_node_id,
                e.category_l1_id,
                p_tenant_type,
                p_tenant_id,
                p_budget_month,
                p_currency
            ) AS bucket,
            SUM(e.amount) AS spent
        FROM expenses e
        WHERE e.tenant_type = p_tenant_type
          AND e.tenant_id = p_tenant_id
          AND e.currency = p_currency
          AND e.deleted_at IS NULL
          AND e.expense_date >= v_month_start
          AND e.expense_date <= v_month_end
        GROUP BY 1
    ) s
    WHERE bucket <> 'unbudgeted';

    RETURN jsonb_build_object(
        'budget_month', to_char(p_budget_month, 'YYYY-MM-DD'),
        'fiscal_period_end', to_char(v_month_end, 'YYYY-MM-DD'),
        'fiscal_start_day', v_fiscal_start_day,
        'days_in_month', v_days_in_month,
        'elapsed_days', v_elapsed,
        'currency', p_currency,
        'total_limit', v_total_limit,
        'total_spent_all', v_total_spent,
        'unbudgeted_spent', v_unbudgeted,
        'has_any_limit', v_has_any_limit,
        'budgets', v_budgets,
        'spent_by_bucket', v_spent_by_bucket
    );
END;
$$;
