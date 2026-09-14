import { expect, test } from "@playwright/test";

test.describe("web.browser.categories_pace_warning", () => {
  test("categories page shows pace warning toggle default off and persists on", async ({
    page,
  }) => {
    const nodes = [
      {
        id: "cat-food",
        code: "food",
        name_ja: "食費",
        level: 1,
        parent_id: null,
        sort_order: 0,
        pace_warning_enabled: false,
        expense_count: 0,
        deletable: true,
      },
      {
        id: "cat-dining",
        code: "dining",
        name_ja: "外食",
        level: 2,
        parent_id: "cat-food",
        sort_order: 0,
        pace_warning_enabled: false,
        expense_count: 0,
        deletable: true,
      },
    ];

    await page.route("**/api/categories?**", async (route) => {
      if (route.request().method() !== "GET") {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ initialized: true, nodes }),
      });
    });

    let patchedBody: unknown = null;
    await page.route("**/api/categories/cat-food", async (route) => {
      if (route.request().method() !== "PATCH") {
        await route.continue();
        return;
      }
      patchedBody = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...nodes[0],
          pace_warning_enabled: true,
        }),
      });
    });

    await page.goto("/categories");
    await expect(page).not.toHaveURL(/\/login/, { timeout: 30_000 });

    const foodToggle = page.locator("#pace-warning-cat-food");
    await expect(foodToggle).toBeVisible({ timeout: 30_000 });
    await expect(foodToggle).not.toBeChecked();
    await expect(
      page.getByRole("checkbox", { name: /LINE alert when spending too fast|支出が早すぎるときにLINEで警告|支出过快时在 LINE 提醒/ }),
    ).toHaveCount(2);
    await expect(page.getByText(/Too-fast alert|早すぎ警告|过快提醒/).first()).toBeVisible();
    await expect(
      page.getByText(/Too-fast spending alert|早すぎる支出の警告|支出过快提醒/),
    ).toBeVisible();

    await foodToggle.check();
    await expect(foodToggle).toBeChecked();
    await expect.poll(() => patchedBody).toEqual({ pace_warning_enabled: true });
  });
});
