-- Group shared expenses schema delta (feature 006)
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS tenant_type text NOT NULL DEFAULT 'user',
    ADD COLUMN IF NOT EXISTS tenant_id text,
    ADD COLUMN IF NOT EXISTS logged_by_line_user_id text;

UPDATE expenses
SET
    tenant_id = line_user_id,
    logged_by_line_user_id = line_user_id
WHERE tenant_id IS NULL OR logged_by_line_user_id IS NULL;

ALTER TABLE expenses
    ALTER COLUMN tenant_id SET NOT NULL,
    ALTER COLUMN logged_by_line_user_id SET NOT NULL;

ALTER TABLE expenses
    DROP CONSTRAINT IF EXISTS expenses_line_user_id_source_message_id_line_item_index_key;

ALTER TABLE expenses
    ADD CONSTRAINT expenses_tenant_message_item_key
    UNIQUE (tenant_type, tenant_id, source_message_id, line_item_index);

CREATE INDEX IF NOT EXISTS idx_expenses_tenant_date
    ON expenses (tenant_type, tenant_id, expense_date)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_expenses_tenant_l1_date
    ON expenses (tenant_type, tenant_id, category_l1_id, expense_date)
    WHERE deleted_at IS NULL;

ALTER TABLE confirmation_messages
    ADD COLUMN IF NOT EXISTS tenant_type text NOT NULL DEFAULT 'user',
    ADD COLUMN IF NOT EXISTS tenant_id text;

UPDATE confirmation_messages
SET tenant_id = line_user_id
WHERE tenant_id IS NULL;

ALTER TABLE confirmation_messages
    ALTER COLUMN tenant_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_confirmation_messages_tenant
    ON confirmation_messages (tenant_type, tenant_id, created_at DESC);

ALTER TABLE processed_reply_messages
    ADD COLUMN IF NOT EXISTS tenant_type text NOT NULL DEFAULT 'user',
    ADD COLUMN IF NOT EXISTS tenant_id text;

UPDATE processed_reply_messages
SET tenant_id = line_user_id
WHERE tenant_id IS NULL;

ALTER TABLE processed_reply_messages
    ALTER COLUMN tenant_id SET NOT NULL;

ALTER TABLE processed_reply_messages
    DROP CONSTRAINT IF EXISTS processed_reply_messages_pkey;

ALTER TABLE processed_reply_messages
    ADD PRIMARY KEY (tenant_type, tenant_id, user_reply_message_id);

CREATE OR REPLACE FUNCTION monthly_expense_total(
    p_tenant_type text,
    p_tenant_id text,
    p_year int,
    p_month int,
    p_category_node_id uuid,
    p_currency char(3)
) RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    cat_level smallint;
    total numeric;
BEGIN
    SELECT level INTO cat_level FROM category_nodes WHERE id = p_category_node_id;
    IF cat_level IS NULL THEN
        RETURN 0;
    END IF;

    SELECT COALESCE(SUM(amount), 0) INTO total
    FROM expenses e
    WHERE e.tenant_type = p_tenant_type
      AND e.tenant_id = p_tenant_id
      AND e.currency = p_currency
      AND e.deleted_at IS NULL
      AND EXTRACT(YEAR FROM e.expense_date) = p_year
      AND EXTRACT(MONTH FROM e.expense_date) = p_month
      AND (
          (cat_level = 1 AND (
              (e.assigned_level = 1 AND e.category_node_id = p_category_node_id)
              OR (e.assigned_level > 1 AND e.category_l1_id = p_category_node_id)
          ))
          OR (cat_level = 2 AND (
              (e.assigned_level = 2 AND e.category_node_id = p_category_node_id)
              OR (e.assigned_level = 3 AND e.category_l2_id = p_category_node_id)
          ))
          OR (cat_level = 3 AND e.assigned_level = 3 AND e.category_node_id = p_category_node_id)
      );

    RETURN total;
END;
$$;

CREATE OR REPLACE FUNCTION yearly_expense_total(
    p_tenant_type text,
    p_tenant_id text,
    p_year int,
    p_category_node_id uuid,
    p_currency char(3)
) RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    cat_level smallint;
    total numeric;
BEGIN
    SELECT level INTO cat_level FROM category_nodes WHERE id = p_category_node_id;
    IF cat_level IS NULL THEN
        RETURN 0;
    END IF;

    SELECT COALESCE(SUM(amount), 0) INTO total
    FROM expenses e
    WHERE e.tenant_type = p_tenant_type
      AND e.tenant_id = p_tenant_id
      AND e.currency = p_currency
      AND e.deleted_at IS NULL
      AND EXTRACT(YEAR FROM e.expense_date) = p_year
      AND (
          (cat_level = 1 AND (
              (e.assigned_level = 1 AND e.category_node_id = p_category_node_id)
              OR (e.assigned_level > 1 AND e.category_l1_id = p_category_node_id)
          ))
          OR (cat_level = 2 AND (
              (e.assigned_level = 2 AND e.category_node_id = p_category_node_id)
              OR (e.assigned_level = 3 AND e.category_l2_id = p_category_node_id)
          ))
          OR (cat_level = 3 AND e.assigned_level = 3 AND e.category_node_id = p_category_node_id)
      );

    RETURN total;
END;
$$;
