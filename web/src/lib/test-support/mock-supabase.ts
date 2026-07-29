/**
 * Shared mocked auth helpers for web PR-lane functional tests.
 * Periodic-expense journeys are out of scope for v1 (FR-015).
 */

export const TEST_USER = {
  id: "test-user-uuid",
  email: "functional-test@example.com",
  app_metadata: {},
  user_metadata: { line_user_id: "U-functional-test" },
  aud: "authenticated",
  created_at: "2026-01-01T00:00:00Z",
};

export function mockAuthUser(user: typeof TEST_USER | null = TEST_USER) {
  return {
    data: { user },
    error: null,
  };
}
