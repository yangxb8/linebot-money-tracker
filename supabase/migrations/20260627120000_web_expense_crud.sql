-- Web dashboard expense CRUD and fiscal-month listing

CREATE OR REPLACE FUNCTION fiscal_period_start_for_date(
    p_expense_date date,
    p_fiscal_start_day smallint
) RETURNS date
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE
        WHEN EXTRACT(DAY FROM p_expense_date)::int >= p_fiscal_start_day THEN
            (date_trunc('month', p_expense_date) + (p_fiscal_start_day - 1) * interval '1 day')::date
        ELSE
            (date_trunc('month', p_expense_date) - interval '1 month' + (p_fiscal_start_day - 1) * interval '1 day')::date
    END;
$$;

CREATE OR REPLACE FUNCTION list_expense_fiscal_months(
    p_tenant_type text,
    p_tenant_id text
) RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_fiscal_start_day smallint;
    v_today date;
    v_current_month date;
    v_months jsonb;
BEGIN
    IF NOT can_access_tenant(p_tenant_type, p_tenant_id) THEN
        RAISE EXCEPTION 'access denied for tenant %:%', p_tenant_type, p_tenant_id;
    END IF;

    v_fiscal_start_day := get_tenant_fiscal_start_day(p_tenant_type, p_tenant_id);
    v_today := (now() AT TIME ZONE 'Asia/Tokyo')::date;
    v_current_month := fiscal_period_start_for_date(v_today, v_fiscal_start_day);

    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'budget_month', to_char(m.budget_month, 'YYYY-MM-DD'),
            'expense_count', m.expense_count,
            'total_amount', m.total_amount
        )
        ORDER BY m.budget_month DESC
    ), '[]'::jsonb)
    INTO v_months
    FROM (
        SELECT
            fiscal_period_start_for_date(e.expense_date, v_fiscal_start_day) AS budget_month,
            COUNT(*)::bigint AS expense_count,
            COALESCE(SUM(e.amount), 0) AS total_amount
        FROM expenses e
        WHERE e.tenant_type = p_tenant_type
          AND e.tenant_id = p_tenant_id
          AND e.currency = 'JPY'
          AND e.deleted_at IS NULL
        GROUP BY 1
    ) m;

    IF NOT EXISTS (
        SELECT 1
        FROM jsonb_array_elements(v_months) elem
        WHERE elem->>'budget_month' = to_char(v_current_month, 'YYYY-MM-DD')
    ) THEN
        v_months := jsonb_build_array(
            jsonb_build_object(
                'budget_month', to_char(v_current_month, 'YYYY-MM-DD'),
                'expense_count', 0,
                'total_amount', 0
            )
        ) || v_months;
    END IF;

    RETURN v_months;
END;
$$;

GRANT EXECUTE ON FUNCTION fiscal_period_start_for_date(date, smallint) TO authenticated;
GRANT EXECUTE ON FUNCTION list_expense_fiscal_months(text, text) TO authenticated;

CREATE POLICY expenses_insert_authenticated
    ON expenses FOR INSERT TO authenticated
    WITH CHECK (
        logged_by_line_user_id = current_line_user_id()
        AND line_user_id = current_line_user_id()
        AND (
            (tenant_type = 'user' AND tenant_id = current_line_user_id())
            OR (
                tenant_type IN ('group', 'room')
                AND EXISTS (
                    SELECT 1 FROM tenant_chat_members tcm
                    WHERE tcm.tenant_type = expenses.tenant_type
                      AND tcm.tenant_id = expenses.tenant_id
                      AND tcm.line_user_id = current_line_user_id()
                )
            )
        )
    );

CREATE POLICY expenses_update_authenticated
    ON expenses FOR UPDATE TO authenticated
    USING (
        (
            tenant_type = 'user'
            AND tenant_id = current_line_user_id()
        )
        OR (
            tenant_type IN ('group', 'room')
            AND EXISTS (
                SELECT 1 FROM tenant_chat_members tcm
                WHERE tcm.tenant_type = expenses.tenant_type
                  AND tcm.tenant_id = expenses.tenant_id
                  AND tcm.line_user_id = current_line_user_id()
            )
        )
    )
    WITH CHECK (
        (
            tenant_type = 'user'
            AND tenant_id = current_line_user_id()
        )
        OR (
            tenant_type IN ('group', 'room')
            AND EXISTS (
                SELECT 1 FROM tenant_chat_members tcm
                WHERE tcm.tenant_type = expenses.tenant_type
                  AND tcm.tenant_id = expenses.tenant_id
                  AND tcm.line_user_id = current_line_user_id()
            )
        )
    );

GRANT INSERT, UPDATE ON expenses TO authenticated;
