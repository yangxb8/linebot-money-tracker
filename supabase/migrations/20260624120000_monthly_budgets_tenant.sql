-- Monthly budgets tenant scope + summary RPC (feature 012)

ALTER TABLE monthly_budgets
    ADD COLUMN IF NOT EXISTS tenant_type text,
    ADD COLUMN IF NOT EXISTS tenant_id text,
    ADD COLUMN IF NOT EXISTS budget_level text,
    ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

UPDATE monthly_budgets b
SET
    tenant_type = 'user',
    tenant_id = b.line_user_id,
    budget_level = CASE cn.level WHEN 1 THEN 'l1' WHEN 2 THEN 'l2' ELSE 'l2' END
FROM category_nodes cn
WHERE cn.id = b.category_node_id
  AND b.tenant_type IS NULL;

ALTER TABLE monthly_budgets
    ALTER COLUMN category_node_id DROP NOT NULL;

ALTER TABLE monthly_budgets DROP CONSTRAINT IF EXISTS monthly_budgets_line_user_id_category_node_id_budget_month_curr_key;
ALTER TABLE monthly_budgets DROP COLUMN IF EXISTS line_user_id;

ALTER TABLE monthly_budgets
    ALTER COLUMN tenant_type SET NOT NULL,
    ALTER COLUMN tenant_id SET NOT NULL,
    ALTER COLUMN budget_level SET NOT NULL;

ALTER TABLE monthly_budgets DROP CONSTRAINT IF EXISTS monthly_budgets_level_check;
ALTER TABLE monthly_budgets
    ADD CONSTRAINT monthly_budgets_level_check
    CHECK (budget_level IN ('total', 'l1', 'l2'));

ALTER TABLE monthly_budgets DROP CONSTRAINT IF EXISTS monthly_budgets_category_level_check;
ALTER TABLE monthly_budgets
    ADD CONSTRAINT monthly_budgets_category_level_check
    CHECK (
        (budget_level = 'total' AND category_node_id IS NULL)
        OR (budget_level IN ('l1', 'l2') AND category_node_id IS NOT NULL)
    );

ALTER TABLE monthly_budgets DROP CONSTRAINT IF EXISTS monthly_budgets_amount_positive;
ALTER TABLE monthly_budgets
    ADD CONSTRAINT monthly_budgets_amount_positive CHECK (amount > 0);

CREATE INDEX IF NOT EXISTS idx_monthly_budgets_tenant_month
    ON monthly_budgets (tenant_type, tenant_id, budget_month);

DROP INDEX IF EXISTS monthly_budgets_total_uq;
CREATE UNIQUE INDEX monthly_budgets_total_uq
    ON monthly_budgets (tenant_type, tenant_id, budget_month, currency)
    WHERE budget_level = 'total';

DROP INDEX IF EXISTS monthly_budgets_category_uq;
CREATE UNIQUE INDEX monthly_budgets_category_uq
    ON monthly_budgets (tenant_type, tenant_id, category_node_id, budget_month, currency)
    WHERE category_node_id IS NOT NULL;

CREATE OR REPLACE FUNCTION resolve_budget_bucket(
    p_assigned_level smallint,
    p_category_node_id uuid,
    p_category_l1_id uuid,
    p_tenant_type text,
    p_tenant_id text,
    p_budget_month date,
    p_currency char(3)
) RETURNS text
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_assigned_level = 2 AND EXISTS (
        SELECT 1
        FROM monthly_budgets mb
        WHERE mb.tenant_type = p_tenant_type
          AND mb.tenant_id = p_tenant_id
          AND mb.budget_month = p_budget_month
          AND mb.currency = p_currency
          AND mb.budget_level = 'l2'
          AND mb.category_node_id = p_category_node_id
    ) THEN
        RETURN 'l2:' || p_category_node_id::text;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM monthly_budgets mb
        WHERE mb.tenant_type = p_tenant_type
          AND mb.tenant_id = p_tenant_id
          AND mb.budget_month = p_budget_month
          AND mb.currency = p_currency
          AND mb.budget_level = 'l1'
          AND mb.category_node_id = p_category_l1_id
    ) THEN
        RETURN 'l1:' || p_category_l1_id::text;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM monthly_budgets mb
        WHERE mb.tenant_type = p_tenant_type
          AND mb.tenant_id = p_tenant_id
          AND mb.budget_month = p_budget_month
          AND mb.currency = p_currency
          AND mb.budget_level = 'total'
    ) THEN
        RETURN 'total';
    END IF;

    RETURN 'unbudgeted';
END;
$$;

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

    v_today := (now() AT TIME ZONE 'Asia/Tokyo')::date;
    v_month_start := date_trunc('month', p_budget_month)::date;
    v_month_end := (date_trunc('month', p_budget_month) + interval '1 month - 1 day')::date;
    v_days_in_month := EXTRACT(DAY FROM v_month_end)::int;

    IF v_today < v_month_start THEN
        v_elapsed := 0;
    ELSIF v_today > v_month_end THEN
        v_elapsed := v_days_in_month;
    ELSE
        v_elapsed := GREATEST(1, EXTRACT(DAY FROM v_today)::int);
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

DROP POLICY IF EXISTS monthly_budgets_select ON monthly_budgets;
DROP POLICY IF EXISTS monthly_budgets_insert ON monthly_budgets;
DROP POLICY IF EXISTS monthly_budgets_update ON monthly_budgets;
DROP POLICY IF EXISTS monthly_budgets_delete ON monthly_budgets;

CREATE POLICY monthly_budgets_select
    ON monthly_budgets FOR SELECT TO authenticated
    USING (can_access_tenant(tenant_type, tenant_id));

CREATE POLICY monthly_budgets_insert
    ON monthly_budgets FOR INSERT TO authenticated
    WITH CHECK (can_access_tenant(tenant_type, tenant_id));

CREATE POLICY monthly_budgets_update
    ON monthly_budgets FOR UPDATE TO authenticated
    USING (can_access_tenant(tenant_type, tenant_id))
    WITH CHECK (can_access_tenant(tenant_type, tenant_id));

CREATE POLICY monthly_budgets_delete
    ON monthly_budgets FOR DELETE TO authenticated
    USING (can_access_tenant(tenant_type, tenant_id));
