import { expect, test } from "@playwright/test";

/**
 * Dashboard attention list should honor pace_warning_enabled:
 * too-fast only when opted in; overspend always listed.
 */
test.describe("web.browser.dashboard_pace_warning_config", () => {
  test("shows opted-in too-fast and overspend; hides too-fast when off", async ({
    page,
  }) => {
    const summary = {
      budget_month: "2026-09-01",
      days_in_month: 30,
      elapsed_days: 15,
      currency: "JPY",
      total: {
        limit: 200000,
        spent: 80000,
        remaining: 120000,
        spent_pct: 0.4,
        has_limit: true,
      },
      categories: [
        {
          node_id: "food",
          code: "food",
          name_ja: "食費",
          level: 1,
          limit: 50000,
          spent: 35000,
          spent_assigned: 0,
          spent_aggregate: 35000,
          suggested_from_children: null,
          has_limit: true,
          pace_warning_enabled: true,
          children: [],
        },
        {
          node_id: "transport",
          code: "transport",
          name_ja: "交通",
          level: 1,
          limit: 50000,
          spent: 35000,
          spent_assigned: 0,
          spent_aggregate: 35000,
          suggested_from_children: null,
          has_limit: true,
          pace_warning_enabled: false,
          children: [],
        },
        {
          node_id: "fixed",
          code: "fixed",
          name_ja: "固定",
          level: 1,
          limit: 50000,
          spent: 60000,
          spent_assigned: 0,
          spent_aggregate: 60000,
          suggested_from_children: null,
          has_limit: true,
          pace_warning_enabled: false,
          children: [],
        },
      ],
      unbudgeted_spent: 0,
      has_any_limit: true,
    };

    await page.route("**/api/**", async (route) => {
      const url = route.request().url();
      if (url.includes("/api/budgets")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(summary),
        });
        return;
      }
      if (url.includes("/api/expenses/fiscal-months")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              budget_month: "2026-09-01",
              total_amount: 80000,
              expense_count: 0,
            },
          ]),
        });
        return;
      }
      if (url.includes("/api/expenses")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
        return;
      }
      if (url.includes("/api/categories")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ initialized: true, nodes: [] }),
        });
        return;
      }
      if (url.includes("/api/settings")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            fiscal_start_day: 1,
            confirmation_show_item_details: true,
          }),
        });
        return;
      }
      if (url.includes("/api/periodic")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/dashboard");
    await expect(page).not.toHaveURL(/\/login/, { timeout: 30_000 });

    // Budget attention card lists food (too-fast + on) and fixed (overspend).
    const attention = page.locator("button").filter({ hasText: "食費" });
    await expect(attention.first()).toBeVisible({ timeout: 30_000 });
    await expect(attention.first().getByText("固定")).toBeVisible();
    await expect(attention.first().getByText("交通")).toHaveCount(0);
  });
});
