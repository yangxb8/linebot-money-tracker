/**
 * web.api.wish_list_mutate
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const listWishListItems = vi.fn();
const createWishListItem = vi.fn();
const parseTenantParams = vi.fn((tenantType: string | null, tenantId: string | null) => {
  if (!tenantType || !tenantId) {
    throw new Response("tenant_type and tenant_id required", { status: 400 });
  }
  return { tenantType, tenantId };
});

vi.mock("@/lib/wish-list/server", () => ({
  listWishListItems: (...args: unknown[]) => listWishListItems(...args),
  createWishListItem: (...args: unknown[]) => createWishListItem(...args),
  parseTenantParams: (a: string | null, b: string | null) => parseTenantParams(a, b),
}));

import { GET, POST } from "@/app/api/wish-list/route";

const sampleItem = {
  id: "wish-1",
  name: "Headphones",
  amount: 15000,
  currency: "JPY",
  category_node_id: "cat-1",
  category_name: "Gadgets",
  product_url: null,
  sort_order: 0,
  status: "active" as const,
  created_at: "2026-07-29T00:00:00Z",
  executed_expense_id: null,
  expense: null,
};

describe("wish-list API functional", () => {
  beforeEach(() => {
    listWishListItems.mockReset();
    createWishListItem.mockReset();
  });

  it("web.api.wish_list_mutate — create then read reflects item", async () => {
    createWishListItem.mockResolvedValue(sampleItem);
    listWishListItems.mockResolvedValue([sampleItem]);

    const createRes = await POST(
      new Request("http://localhost/api/wish-list", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_type: "user",
          tenant_id: "U1",
          name: "Headphones",
          amount: 15000,
          category_node_id: "cat-1",
        }),
      }),
    );
    expect(createRes.status).toBe(201);
    const created = await createRes.json();
    expect(created.name).toBe("Headphones");

    const listRes = await GET(
      new Request("http://localhost/api/wish-list?tenant_type=user&tenant_id=U1"),
    );
    expect(listRes.status).toBe(200);
    const listed = await listRes.json();
    expect(listed.items).toHaveLength(1);
    expect(listed.items[0].id).toBe("wish-1");
  });
});
