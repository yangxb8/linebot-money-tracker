import { describe, expect, it } from "vitest";
import { buildCategorySpentTotals, enrichBudgetSummary } from "@/lib/budget/server";
import type { RpcBudgetSummary } from "@/lib/budget/types";

describe("buildCategorySpentTotals", () => {
  it("rolls L2 expenses up to both L1 and L2 totals", () => {
    const totals = buildCategorySpentTotals([
      {
        assigned_level: 2,
        category_node_id: "l2-groceries",
        category_l1_id: "l1-food",
        amount: 1500,
      },
      {
        assigned_level: 1,
        category_node_id: "l1-food",
        category_l1_id: "l1-food",
        amount: 500,
      },
    ]);

    expect(totals.byL2["l2-groceries"]).toBe(1500);
    expect(totals.byL1["l1-food"]).toBe(2000);
  });
});

describe("enrichBudgetSummary", () => {
  it("uses category totals for card spent values", () => {
    const rpc: RpcBudgetSummary = {
      budget_month: "2026-06-01",
      days_in_month: 30,
      elapsed_days: 10,
      currency: "JPY",
      total_limit: null,
      total_spent_all: 2000,
      unbudgeted_spent: 0,
      has_any_limit: true,
      budgets: [
        { budget_level: "l1", category_node_id: "l1-food", amount: 10000 },
        { budget_level: "l2", category_node_id: "l2-groceries", amount: 5000 },
      ],
      spent_by_bucket: {
        "l2:l2-groceries": 1500,
      },
    };
    const nodes = [
      {
        id: "l1-food",
        code: "food",
        name_ja: "食費",
        level: 1,
        parent_id: null,
        sort_order: 1,
      },
      {
        id: "l2-groceries",
        code: "food.groceries",
        name_ja: "スーパー",
        level: 2,
        parent_id: "l1-food",
        sort_order: 1,
      },
    ];
    const categorySpent = buildCategorySpentTotals([
      {
        assigned_level: 2,
        category_node_id: "l2-groceries",
        category_l1_id: "l1-food",
        amount: 1500,
      },
    ]);

    const summary = enrichBudgetSummary(rpc, nodes, categorySpent);
    const food = summary.categories[0];
    const groceries = food.children?.[0];

    expect(groceries?.spent_aggregate).toBe(1500);
    expect(food.spent_aggregate).toBe(1500);
    expect(food.spent).toBe(1500);
    expect(summary.lazy_copied_from_previous).toBe(false);
  });

  it("passes through lazy_copied_from_previous from the RPC", () => {
    const rpc: RpcBudgetSummary = {
      budget_month: "2026-07-24",
      days_in_month: 31,
      elapsed_days: 1,
      currency: "JPY",
      total_limit: 100000,
      total_spent_all: 0,
      unbudgeted_spent: 0,
      has_any_limit: true,
      lazy_copied_from_previous: true,
      budgets: [{ budget_level: "total", category_node_id: null, amount: 100000 }],
      spent_by_bucket: {},
    };

    const summary = enrichBudgetSummary(rpc, []);
    expect(summary.lazy_copied_from_previous).toBe(true);
    expect(summary.has_any_limit).toBe(true);
  });
});
