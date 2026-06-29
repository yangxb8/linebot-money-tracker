import type { CategoryNode } from "@/lib/categories/types";
import { categoryLabel } from "@/lib/dashboard/format";
import type { ExpenseRecord } from "@/lib/expenses/types";

export type ExpenseSortField = "date" | "amount";
export type ExpenseSortDir = "asc" | "desc";

export type ExpenseGroup = {
  key: string;
  label: string;
  total: number;
  items: ExpenseRecord[];
};

export function compareExpenses(
  a: ExpenseRecord,
  b: ExpenseRecord,
  field: ExpenseSortField,
  dir: ExpenseSortDir,
): number {
  const mul = dir === "asc" ? 1 : -1;
  if (field === "amount") {
    return mul * (Number(a.amount) - Number(b.amount));
  }
  const dateCmp = a.expense_date.localeCompare(b.expense_date);
  if (dateCmp !== 0) return mul * dateCmp;
  return mul * a.id.localeCompare(b.id);
}

export function sortExpenses(
  rows: ExpenseRecord[],
  field: ExpenseSortField,
  dir: ExpenseSortDir,
): ExpenseRecord[] {
  return [...rows].sort((a, b) => compareExpenses(a, b, field, dir));
}

function categoryOrderKeys(categories: CategoryNode[]): string[] {
  const l1Nodes = categories
    .filter((node) => node.level === 1)
    .sort((a, b) => {
      if (a.code === "unknown" && b.code !== "unknown") return 1;
      if (b.code === "unknown" && a.code !== "unknown") return -1;
      return a.sort_order - b.sort_order;
    });

  const childrenByParent = new Map<string, CategoryNode[]>();
  for (const node of categories) {
    if (node.level === 2 && node.parent_id) {
      const list = childrenByParent.get(node.parent_id) ?? [];
      list.push(node);
      childrenByParent.set(node.parent_id, list);
    }
  }
  for (const [, list] of childrenByParent) {
    list.sort((a, b) => a.sort_order - b.sort_order);
  }

  const keys: string[] = [];
  for (const l1 of l1Nodes) {
    const children = childrenByParent.get(l1.id) ?? [];
    for (const l2 of children) {
      keys.push(l2.id);
    }
    keys.push(l1.id);
  }
  return keys;
}

export function groupExpensesByCategory(
  rows: ExpenseRecord[],
  categories: CategoryNode[],
): ExpenseGroup[] {
  const map = new Map<string, ExpenseGroup>();
  for (const row of rows) {
    const key = row.category_node_id;
    const existing = map.get(key);
    if (existing) {
      existing.total += Number(row.amount);
      existing.items.push(row);
    } else {
      map.set(key, {
        key,
        label: categoryLabel(row),
        total: Number(row.amount),
        items: [row],
      });
    }
  }

  const orderKeys = categoryOrderKeys(categories);
  const ordered: ExpenseGroup[] = [];
  const seen = new Set<string>();

  for (const key of orderKeys) {
    const group = map.get(key);
    if (group) {
      ordered.push(group);
      seen.add(key);
    }
  }

  const remaining = [...map.values()]
    .filter((group) => !seen.has(group.key))
    .sort((a, b) => a.label.localeCompare(b.label));

  return [...ordered, ...remaining];
}
