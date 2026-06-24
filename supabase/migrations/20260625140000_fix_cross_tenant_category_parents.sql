-- Repair L2 categories whose parent_id points at another tenant's L1 copy.
-- This happened when the web UI created categories while stale categories
-- from a previous tenant were still on screen.

UPDATE category_nodes AS child
SET parent_id = tenant_parent.id
FROM category_nodes AS wrong_parent,
     category_nodes AS tenant_parent
WHERE child.level = 2
  AND child.parent_id = wrong_parent.id
  AND (
    wrong_parent.tenant_type IS DISTINCT FROM child.tenant_type
    OR wrong_parent.tenant_id IS DISTINCT FROM child.tenant_id
  )
  AND tenant_parent.tenant_type = child.tenant_type
  AND tenant_parent.tenant_id = child.tenant_id
  AND tenant_parent.level = 1
  AND tenant_parent.code = wrong_parent.code;
