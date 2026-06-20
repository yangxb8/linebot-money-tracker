-- Fix dashboard 403: RLS policies call current_line_user_id() as the
-- authenticated role, which requires EXECUTE on the function.
-- Migration 20260619120000 revoked it from authenticated, breaking reads.

GRANT EXECUTE ON FUNCTION current_line_user_id() TO authenticated;
