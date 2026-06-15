-- Limit category taxonomy to 2 levels; migrate L3 expenses and references to L2 parents.

CREATE OR REPLACE FUNCTION _remap_legacy_category_code(code text) RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE code
        WHEN 'food.dining.cafe' THEN 'food.dining'
        WHEN 'food.dining.restaurant' THEN 'food.dining'
        WHEN 'food.dining.fastfood' THEN 'food.dining'
        ELSE code
    END;
$$;

-- Expenses assigned at L3 → parent L2 node.
UPDATE expenses
SET
    category_node_id = category_l2_id,
    assigned_level = 2,
    category_l3_id = NULL
WHERE assigned_level = 3
  AND category_l2_id IS NOT NULL;

-- Budgets targeting L3 nodes → parent L2.
UPDATE monthly_budgets b
SET category_node_id = cn.parent_id
FROM category_nodes cn
WHERE b.category_node_id = cn.id
  AND cn.level = 3
  AND cn.parent_id IS NOT NULL;

-- Confirmation snapshots: remap stored category codes.
UPDATE confirmation_messages
SET items_snapshot = (
    SELECT COALESCE(
        jsonb_agg(
            jsonb_set(
                jsonb_set(
                    elem,
                    '{category_guess_code}',
                    to_jsonb(_remap_legacy_category_code(elem->>'category_guess_code'))
                ),
                '{category_alternatives}',
                COALESCE(
                    (
                        SELECT jsonb_agg(to_jsonb(_remap_legacy_category_code(alt)))
                        FROM jsonb_array_elements_text(
                            COALESCE(elem->'category_alternatives', '[]'::jsonb)
                        ) AS alt
                    ),
                    '[]'::jsonb
                )
            )
        ),
        '[]'::jsonb
    )
    FROM jsonb_array_elements(items_snapshot) AS elem
)
WHERE items_snapshot IS NOT NULL;

UPDATE confirmation_messages
SET pending_payload = jsonb_set(
    pending_payload,
    '{category_options}',
    COALESCE(
        (
            SELECT jsonb_agg(to_jsonb(_remap_legacy_category_code(opt)))
            FROM jsonb_array_elements_text(pending_payload->'category_options') AS opt
        ),
        '[]'::jsonb
    )
)
WHERE pending_payload ? 'category_options';

-- Remove L3 taxonomy nodes.
DELETE FROM category_nodes
WHERE level = 3;

ALTER TABLE category_nodes
    DROP CONSTRAINT IF EXISTS category_nodes_level_check;

ALTER TABLE category_nodes
    ADD CONSTRAINT category_nodes_level_check CHECK (level BETWEEN 1 AND 2);

ALTER TABLE expenses
    DROP CONSTRAINT IF EXISTS expenses_assigned_level_check;

ALTER TABLE expenses
    ADD CONSTRAINT expenses_assigned_level_check CHECK (assigned_level BETWEEN 1 AND 2);

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
              OR (e.assigned_level = 2 AND e.category_l1_id = p_category_node_id)
          ))
          OR (cat_level = 2 AND e.assigned_level = 2 AND e.category_node_id = p_category_node_id)
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
              OR (e.assigned_level = 2 AND e.category_l1_id = p_category_node_id)
          ))
          OR (cat_level = 2 AND e.assigned_level = 2 AND e.category_node_id = p_category_node_id)
      );

    RETURN total;
END;
$$;

DROP VIEW IF EXISTS v_expenses_enriched;

CREATE VIEW v_expenses_enriched AS
SELECT
    e.*,
    cn.code AS category_code,
    cn.name_ja AS category_name_ja,
    l1.name_ja AS category_l1_name,
    l2.name_ja AS category_l2_name
FROM expenses e
JOIN category_nodes cn ON cn.id = e.category_node_id
JOIN category_nodes l1 ON l1.id = e.category_l1_id
LEFT JOIN category_nodes l2 ON l2.id = e.category_l2_id;

DROP FUNCTION IF EXISTS _remap_legacy_category_code(text);
