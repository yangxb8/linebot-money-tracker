import { describe, expect, it } from "vitest";
import { bucketKey, resolveBudgetBucket } from "@/lib/budget/cascade";
import type { BudgetLimitRow } from "@/lib/budget/types";

const budgets: BudgetLimitRow[] = [
  { budget_level: "total", category_node_id: null, amount: 100000 },
  { budget_level: "l1", category_node_id: "l1-food", amount: 50000 },
  { budget_level: "l2", category_node_id: "l2-dining", amount: 20000 },
];

describe("resolveBudgetBucket", () => {
  it("assigns L2 expense to L2 budget when present", () => {
    const bucket = resolveBudgetBucket(
      {
        assigned_level: 2,
        category_node_id: "l2-dining",
        category_l1_id: "l1-food",
      },
      budgets,
    );
    expect(bucket).toEqual({ kind: "l2", categoryNodeId: "l2-dining" });
    expect(bucketKey(bucket)).toBe("l2:l2-dining");
  });

  it("falls back to L1 when no L2 budget for category", () => {
    const bucket = resolveBudgetBucket(
      {
        assigned_level: 2,
        category_node_id: "l2-grocery",
        category_l1_id: "l1-food",
      },
      budgets,
    );
    expect(bucket).toEqual({ kind: "l1", categoryNodeId: "l1-food" });
  });

  it("uses total when only total budget exists", () => {
    const bucket = resolveBudgetBucket(
      {
        assigned_level: 2,
        category_node_id: "l2-other",
        category_l1_id: "l1-other",
      },
      [{ budget_level: "total", category_node_id: null, amount: 80000 }],
    );
    expect(bucket).toEqual({ kind: "total" });
  });

  it("returns unbudgeted when no matching limits", () => {
    const bucket = resolveBudgetBucket(
      {
        assigned_level: 1,
        category_node_id: "l1-other",
        category_l1_id: "l1-other",
      },
      [],
    );
    expect(bucket).toEqual({ kind: "unbudgeted" });
  });

  it("assigns L1 expense to L1 budget", () => {
    const bucket = resolveBudgetBucket(
      {
        assigned_level: 1,
        category_node_id: "l1-food",
        category_l1_id: "l1-food",
      },
      budgets,
    );
    expect(bucket).toEqual({ kind: "l1", categoryNodeId: "l1-food" });
  });

  it("L1 expense skips L2 and uses L1 when L2 budget exists for sibling", () => {
    const bucket = resolveBudgetBucket(
      {
        assigned_level: 1,
        category_node_id: "l1-food",
        category_l1_id: "l1-food",
      },
      [{ budget_level: "l2", category_node_id: "l2-dining", amount: 20000 }],
    );
    expect(bucket).toEqual({ kind: "unbudgeted" });
  });
});
