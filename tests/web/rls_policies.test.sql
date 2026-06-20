-- RLS verification fixtures for web dashboard (feature 009)
-- Run sections manually in Supabase SQL editor or via integration tests.
-- Expected: authenticated user A cannot read user B personal expenses.

-- 1. current_line_user_id() returns NULL without auth session
SELECT current_line_user_id() AS unauthenticated_line_user_id;
-- Expected: NULL

-- 2. Personal ledger policy shape (documentation)
-- Authenticated user with line_user_id = 'USER_A' should see:
--   tenant_type = 'user' AND tenant_id = 'USER_A'
-- Authenticated user should NOT see:
--   tenant_type = 'user' AND tenant_id = 'USER_B'

-- 3. Shared ledger policy shape (documentation)
-- User in tenant_chat_members (group, G1, USER_A) should see group G1 expenses.
-- User not in tenant_chat_members for G1 should see zero rows for that tenant.

-- 4. Cross-tenant denial (run via Supabase JS client as USER_A, not SQL editor)
-- const { data } = await supabase
--   .from('v_expenses_enriched')
--   .select('id')
--   .eq('tenant_type', 'user')
--   .eq('tenant_id', 'OTHER_USER_ID');
-- Expected: [] (RLS filters unauthorized rows)

-- 5. Soft-deleted rows excluded by app query (deleted_at IS NULL filter in client)
-- RLS may still allow deleted rows; dashboard client must filter deleted_at.
