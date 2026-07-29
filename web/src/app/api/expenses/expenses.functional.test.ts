/**
 * web.api.unauthorized + web.api.expenses_overview
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const listExpenses = vi.fn();
const parseTenantParams = vi.fn((tenantType: string | null, tenantId: string | null) => {
  if (!tenantType || !tenantId) {
    throw new Response("tenant_type and tenant_id required", { status: 400 });
  }
  return { tenantType, tenantId };
});

vi.mock("@/lib/expenses/server", () => ({
  listExpenses: (...args: unknown[]) => listExpenses(...args),
  parseTenantParams: (a: string | null, b: string | null) => parseTenantParams(a, b),
  createExpense: vi.fn(),
}));

import { GET } from "@/app/api/expenses/route";

describe("expenses API functional", () => {
  beforeEach(() => {
    listExpenses.mockReset();
  });

  it("web.api.unauthorized — returns 401 when requireExpenseUser fails", async () => {
    listExpenses.mockRejectedValue(new Response("Unauthorized", { status: 401 }));
    const response = await GET(
      new Request(
        "http://localhost/api/expenses?tenant_type=user&tenant_id=U1&budget_month=2026-07-01",
      ),
    );
    expect(response.status).toBe(401);
  });

  it("web.api.expenses_overview — returns 200 list or empty", async () => {
    listExpenses.mockResolvedValue([]);
    const response = await GET(
      new Request(
        "http://localhost/api/expenses?tenant_type=user&tenant_id=U1&budget_month=2026-07-01",
      ),
    );
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body).toEqual([]);
  });
});
