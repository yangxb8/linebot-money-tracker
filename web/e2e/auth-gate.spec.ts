import { expect, test } from "@playwright/test";

test.describe("web.browser.auth_gate", () => {
  test("unauthenticated protected URL redirects to login", async ({ page }) => {
    await page.route("**/auth/v1/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ user: null }),
      });
    });

    // e2e_unauth bypasses NEXT_PUBLIC_E2E_MOCK_LINE_USER_ID used by signed-in smoke.
    await page.goto("/dashboard?e2e_unauth=1");
    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
  });
});
