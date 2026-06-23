-- RLS verification for monthly_budgets (feature 012)
-- Run manually in Supabase SQL editor with test users configured.

-- Expect: personal owner can SELECT own budgets
-- SELECT * FROM monthly_budgets
-- WHERE tenant_type = 'user' AND tenant_id = current_line_user_id();

-- Expect: 0 rows for another user's personal tenant
-- SELECT * FROM monthly_budgets
-- WHERE tenant_type = 'user' AND tenant_id = '<other_line_user_id>';

-- Expect: group member can SELECT group budgets
-- SELECT * FROM monthly_budgets
-- WHERE tenant_type = 'group' AND tenant_id = '<group_id>';
