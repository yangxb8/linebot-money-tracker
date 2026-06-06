-- Expense reply edits schema delta (feature 005)
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz,
    ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_expenses_active_user_date
    ON expenses (line_user_id, expense_date)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS confirmation_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_message_id text UNIQUE NOT NULL,
    line_user_id text NOT NULL,
    confirmation_text text NOT NULL,
    items_snapshot jsonb NOT NULL,
    pending_action text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_confirmation_messages_user
    ON confirmation_messages (line_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS confirmation_expenses (
    confirmation_id uuid NOT NULL REFERENCES confirmation_messages (id) ON DELETE CASCADE,
    expense_id uuid NOT NULL REFERENCES expenses (id),
    line_item_index int NOT NULL,
    PRIMARY KEY (confirmation_id, expense_id)
);

CREATE TABLE IF NOT EXISTS reply_edit_audit (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    confirmation_id uuid NOT NULL REFERENCES confirmation_messages (id),
    line_user_id text NOT NULL,
    user_reply_message_id text NOT NULL,
    user_reply_text text NOT NULL,
    intent_json jsonb NOT NULL,
    result_status text NOT NULL,
    result_summary text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS processed_reply_messages (
    line_user_id text NOT NULL,
    user_reply_message_id text NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (line_user_id, user_reply_message_id)
);

ALTER TABLE confirmation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE confirmation_expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE reply_edit_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_reply_messages ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION monthly_expense_total(
    p_line_user_id text,
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
    WHERE e.line_user_id = p_line_user_id
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
    p_line_user_id text,
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
    WHERE e.line_user_id = p_line_user_id
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
