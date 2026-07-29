import { expect, test } from "@playwright/test";

test.describe("web.browser.signed_in_smoke", () => {
  test.use({
    // Env is set on webServer in playwright.config; also assert via header check.
  });

  test("mocked signed-in session loads dashboard without auth bounce", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await expect(page).not.toHaveURL(/\/login/, { timeout: 30_000 });
    // Stay on an app route (dashboard or tenant redirect target).
    await expect(page).toHaveURL(/\/(dashboard|wish-list|budget|categories|settings)/);
  });
});
