-- RLS verification for periodic_expense_schedules (feature 011)
-- Run manually in Supabase SQL editor with test users configured.

-- Expect: personal owner can SELECT own schedules
-- SET request.jwt.claim.sub = '<auth_user_uuid>';
-- SELECT * FROM periodic_expense_schedules
-- WHERE tenant_type = 'user' AND tenant_id = current_line_user_id();

-- Expect: 0 rows for another user's personal tenant
-- SELECT * FROM periodic_expense_schedules
-- WHERE tenant_type = 'user' AND tenant_id = '<other_line_user_id>';

-- Expect: group member can SELECT group schedules
-- SELECT * FROM periodic_expense_schedules
-- WHERE tenant_type = 'group' AND tenant_id = '<group_id>';

-- Idempotency: run process_due_periodic_schedules twice with same action payload
-- Second run should report skipped >= 1 and no duplicate expense rows:
-- SELECT count(*) FROM expenses
-- WHERE periodic_schedule_id = '<schedule_id>' AND expense_date = '<date>';
