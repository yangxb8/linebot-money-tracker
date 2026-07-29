/**
 * web.api.budgets
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const summary = {
  budget_month: "2026-07-01",
  currency: "JPY",
  rows: [],
  total_limit: 100000,
  total_spent: 0,
};

const fetchBudgetSummary = vi.fn(async () => summary);
const upsertBudgetRows = vi.fn(async () => undefined);
const parseTenantParams = vi.fn((tenantType: string | null, tenantId: string | null) => {
  if (!tenantType || !tenantId) {
    throw new Response("tenant_type and tenant_id required", { status: 400 });
  }
  return { tenantType, tenantId };
});
const fetchTenantSettings = vi.fn(async () => ({
  fiscal_start_day: 1,
  confirmation_show_item_details: true,
}));
const isCurrentBudgetMonth = vi.fn(() => true);
const currentBudgetMonthJst = vi.fn(() => "2026-07-01");

vi.mock("@/lib/budget/server", () => ({
  fetchBudgetSummary: (...args: unknown[]) => fetchBudgetSummary(...args),
  upsertBudgetRows: (...args: unknown[]) => upsertBudgetRows(...args),
  parseTenantParams: (a: string | null, b: string | null) => parseTenantParams(a, b),
}));

vi.mock("@/lib/settings/server", () => ({
  fetchTenantSettings: (...args: unknown[]) => fetchTenantSettings(...args),
}));

vi.mock("@/lib/budget/format", () => ({
  currentBudgetMonthJst: (...args: unknown[]) => currentBudgetMonthJst(...args),
  isCurrentBudgetMonth: (...args: unknown[]) => isCurrentBudgetMonth(...args),
}));

import { GET, PUT } from "@/app/api/budgets/route";

describe("budgets API functional", () => {
  beforeEach(() => {
    fetchBudgetSummary.mockClear();
    upsertBudgetRows.mockClear();
  });

  it("web.api.budgets — read/update succeeds", async () => {
    const getRes = await GET(
      new Request(
        "http://localhost/api/budgets?tenant_type=user&tenant_id=U1&budget_month=2026-07-01",
      ),
    );
    expect(getRes.status).toBe(200);
    const body = await getRes.json();
    expect(body.budget_month).toBe("2026-07-01");

    const putRes = await PUT(
      new Request("http://localhost/api/budgets", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_type: "user",
          tenant_id: "U1",
          budget_month: "2026-07-01",
          currency: "JPY",
          budgets: [{ budget_level: "total", category_node_id: null, amount: 100000 }],
          clear_levels: [],
        }),
      }),
    );
    expect(putRes.status).toBe(200);
    expect(upsertBudgetRows).toHaveBeenCalled();
  });
});
