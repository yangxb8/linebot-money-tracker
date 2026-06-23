import type { BudgetBucket, BudgetLevel, BudgetLimitRow } from "@/lib/budget/types";

export type ExpenseForBucket = {
  assigned_level: number;
  category_node_id: string;
  category_l1_id: string;
};

function hasBudget(
  budgets: BudgetLimitRow[],
  level: BudgetLevel,
  categoryNodeId: string | null,
): boolean {
  return budgets.some(
    (b) =>
      b.budget_level === level &&
      (level === "total"
        ? b.category_node_id == null
        : b.category_node_id === categoryNodeId),
  );
}

export function resolveBudgetBucket(
  expense: ExpenseForBucket,
  budgets: BudgetLimitRow[],
): BudgetBucket {
  if (
    expense.assigned_level === 2 &&
    hasBudget(budgets, "l2", expense.category_node_id)
  ) {
    return { kind: "l2", categoryNodeId: expense.category_node_id };
  }

  if (hasBudget(budgets, "l1", expense.category_l1_id)) {
    return { kind: "l1", categoryNodeId: expense.category_l1_id };
  }

  if (hasBudget(budgets, "total", null)) {
    return { kind: "total" };
  }

  return { kind: "unbudgeted" };
}

export function bucketKey(bucket: BudgetBucket): string {
  if (bucket.kind === "total") return "total";
  if (bucket.kind === "unbudgeted") return "unbudgeted";
  return `${bucket.kind}:${bucket.categoryNodeId}`;
}

export function parseBucketKey(key: string): BudgetBucket {
  if (key === "total") return { kind: "total" };
  if (key === "unbudgeted") return { kind: "unbudgeted" };
  const [kind, id] = key.split(":");
  if (kind === "l1" && id) return { kind: "l1", categoryNodeId: id };
  if (kind === "l2" && id) return { kind: "l2", categoryNodeId: id };
  return { kind: "unbudgeted" };
}
