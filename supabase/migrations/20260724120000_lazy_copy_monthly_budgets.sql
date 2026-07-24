-- Lazy-copy monthly budgets from the previous fiscal period when the
-- current period has none. Used by get_budget_summary (web) and the bot.

CREATE OR REPLACE FUNCTION current_fiscal_period_start(
    p_tenant_type text,
    p_tenant_id text,
    p_today date DEFAULT ((now() AT TIME ZONE 'Asia/Tokyo')::date)
) RETURNS date
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_fiscal_start_day smallint;
    v_year int;
    v_month int;
BEGIN
    v_fiscal_start_day := get_tenant_fiscal_start_day(p_tenant_type, p_tenant_id);
    v_year := EXTRACT(YEAR FROM p_today)::int;
    v_month := EXTRACT(MONTH FROM p_today)::int;

    IF EXTRACT(DAY FROM p_today)::int < v_fiscal_start_day THEN
        IF v_month = 1 THEN
            v_year := v_year - 1;
            v_month := 12;
        ELSE
            v_month := v_month - 1;
        END IF;
    END IF;

    RETURN make_date(v_year, v_month, v_fiscal_start_day);
END;
$$;

CREATE OR REPLACE FUNCTION lazy_copy_monthly_budgets(
    p_tenant_type text,
    p_tenant_id text,
    p_budget_month date,
    p_currency char(3) DEFAULT 'JPY'
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_prev_month date;
    v_inserted int := 0;
    v_current_start date;
BEGIN
    IF NOT (
        auth.role() = 'service_role'
        OR can_access_tenant(p_tenant_type, p_tenant_id)
    ) THEN
        RAISE EXCEPTION 'access denied for tenant %:%', p_tenant_type, p_tenant_id;
    END IF;

    -- Only auto-fill the tenant's active fiscal period.
    v_current_start := current_fiscal_period_start(p_tenant_type, p_tenant_id);
    IF p_budget_month <> v_current_start THEN
        RETURN false;
    END IF;

    -- Serialize concurrent first-access copies for the same tenant/month.
    PERFORM pg_advisory_xact_lock(
        hashtext(p_tenant_type || ':' || p_tenant_id || ':' || p_budget_month::text)
    );

    IF EXISTS (
        SELECT 1
        FROM monthly_budgets mb
        WHERE mb.tenant_type = p_tenant_type
          AND mb.tenant_id = p_tenant_id
          AND mb.budget_month = p_budget_month
          AND mb.currency = p_currency
    ) THEN
        RETURN false;
    END IF;

    v_prev_month := (p_budget_month - interval '1 month')::date;

    IF NOT EXISTS (
        SELECT 1
        FROM monthly_budgets mb
        WHERE mb.tenant_type = p_tenant_type
          AND mb.tenant_id = p_tenant_id
          AND mb.budget_month = v_prev_month
          AND mb.currency = p_currency
    ) THEN
        RETURN false;
    END IF;

    INSERT INTO monthly_budgets (
        tenant_type,
        tenant_id,
        budget_month,
        currency,
        budget_level,
        category_node_id,
        amount
    )
    SELECT
        p_tenant_type,
        p_tenant_id,
        p_budget_month,
        p_currency,
        mb.budget_level,
        mb.category_node_id,
        mb.amount
    FROM monthly_budgets mb
    WHERE mb.tenant_type = p_tenant_type
      AND mb.tenant_id = p_tenant_id
      AND mb.budget_month = v_prev_month
      AND mb.currency = p_currency
      AND (
          mb.category_node_id IS NULL
          OR EXISTS (
              SELECT 1
              FROM category_nodes cn
              WHERE cn.id = mb.category_node_id
                AND cn.tenant_type = p_tenant_type
                AND cn.tenant_id = p_tenant_id
          )
      );

    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    RETURN v_inserted > 0;
END;
$$;

GRANT EXECUTE ON FUNCTION current_fiscal_period_start(text, text, date) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION lazy_copy_monthly_budgets(text, text, date, character) TO authenticated, service_role;

-- get_budget_summary becomes VOLATILE so it can lazy-copy on read.
CREATE OR REPLACE FUNCTION get_budget_summary(
    p_tenant_type text,
    p_tenant_id text,
    p_budget_month date,
    p_currency char(3) DEFAULT 'JPY'
) RETURNS jsonb
LANGUAGE plpgsql
VOLATILE
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
    v_lazy_copied boolean := false;
BEGIN
    IF NOT (
        auth.role() = 'service_role'
        OR can_access_tenant(p_tenant_type, p_tenant_id)
    ) THEN
        RAISE EXCEPTION 'access denied for tenant %:%', p_tenant_type, p_tenant_id;
    END IF;

    v_lazy_copied := lazy_copy_monthly_budgets(
        p_tenant_type,
        p_tenant_id,
        p_budget_month,
        p_currency
    );

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
        'lazy_copied_from_previous', v_lazy_copied,
        'budgets', v_budgets,
        'spent_by_bucket', v_spent_by_bucket
    );
END;
$$;
