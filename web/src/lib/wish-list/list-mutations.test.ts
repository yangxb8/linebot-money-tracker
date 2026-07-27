import { describe, expect, it } from "vitest";
import {
  compareWishListItems,
  reorderWishListItemIds,
  removeWishListItem,
  sortWishListItems,
  upsertWishListItem,
} from "@/lib/wish-list/list-mutations";
import type { WishListItem } from "@/lib/wish-list/types";

function item(
  overrides: Partial<WishListItem> & Pick<WishListItem, "id">,
): WishListItem {
  return {
    name: "Item",
    amount: 1000,
    currency: "JPY",
    category_node_id: "cat-1",
    category_name: "Food",
    product_url: null,
    sort_order: 0,
    status: "active",
    created_at: "2026-07-01T00:00:00.000Z",
    executed_expense_id: null,
    expense: null,
    ...overrides,
  };
}

describe("wish list list-mutations", () => {
  it("sorts by priority, then created_at", () => {
    const rows = sortWishListItems(
      [
        item({ id: "b", sort_order: 1, created_at: "2026-07-02T00:00:00.000Z" }),
        item({ id: "a", sort_order: 0, created_at: "2026-07-03T00:00:00.000Z" }),
      ],
      "priority",
    );
    expect(rows.map((row) => row.id)).toEqual(["a", "b"]);
  });

  it("sorts by price descending", () => {
    const rows = sortWishListItems(
      [
        item({ id: "cheap", amount: 500 }),
        item({ id: "dear", amount: 2000 }),
      ],
      "price",
    );
    expect(rows.map((row) => row.id)).toEqual(["dear", "cheap"]);
  });

  it("upserts and re-sorts edited items", () => {
    const rows = upsertWishListItem(
      [item({ id: "a", amount: 500 }), item({ id: "b", amount: 2000 })],
      item({ id: "a", amount: 3000 }),
      "price",
    );
    expect(rows.map((row) => row.id)).toEqual(["a", "b"]);
    expect(compareWishListItems(rows[0], rows[1], "price")).toBeLessThan(0);
  });

  it("removes an item by id", () => {
    const rows = removeWishListItem(
      [item({ id: "a" }), item({ id: "b" })],
      "a",
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].id).toBe("b");
  });

  it("reorders items and updates sort_order", () => {
    const rows = reorderWishListItemIds(
      [item({ id: "a", sort_order: 0 }), item({ id: "b", sort_order: 1 })],
      ["b", "a"],
    );
    expect(rows.map((row) => row.id)).toEqual(["b", "a"]);
    expect(rows[0].sort_order).toBe(0);
    expect(rows[1].sort_order).toBe(1);
  });
});
