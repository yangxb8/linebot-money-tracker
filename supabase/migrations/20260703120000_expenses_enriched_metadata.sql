-- Expose expenses.metadata (and other columns added after the view was pinned) via v_expenses_enriched.
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

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

GRANT SELECT ON v_expenses_enriched TO authenticated;
ALTER VIEW v_expenses_enriched SET (security_invoker = true);
