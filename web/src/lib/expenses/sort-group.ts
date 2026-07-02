import type { CategoryNode } from "@/lib/categories/types";
import { categoryLabel } from "@/lib/dashboard/format";
import type { ExpenseRecord } from "@/lib/expenses/types";

export type ExpenseSortField = "date" | "amount";
export type ExpenseSortDir = "asc" | "desc";

export type ExpenseListSort = {
  field: ExpenseSortField;
  dir: ExpenseSortDir;
};

export const DEFAULT_EXPENSE_LIST_SORT: ExpenseListSort = {
  field: "date",
  dir: "desc",
};

export function parseExpenseListSort(
  field: string | null | undefined,
  dir: string | null | undefined,
): ExpenseListSort {
  return {
    field: field === "amount" ? "amount" : "date",
    dir: dir === "asc" ? "asc" : "desc",
  };
}

export type ExpenseGroup = {
  key: string;
  label: string;
  total: number;
  items: ExpenseRecord[];
};

export type ExpenseL2Group = {
  key: string;
  label: string;
  total: number;
  items: ExpenseRecord[];
};

export type ExpenseL1Group = {
  key: string;
  label: string;
  total: number;
  itemCount: number;
  l2Groups: ExpenseL2Group[];
  directItems: ExpenseRecord[];
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

function isUnknownCategoryId(id: string, categories: CategoryNode[]): boolean {
  const node = categories.find((category) => category.id === id);
  return node?.code === "unknown";
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

function l1OrderKeys(categories: CategoryNode[]): string[] {
  return categories
    .filter((node) => node.level === 1)
    .sort((a, b) => {
      if (a.code === "unknown" && b.code !== "unknown") return 1;
      if (b.code === "unknown" && a.code !== "unknown") return -1;
      return a.sort_order - b.sort_order;
    })
    .map((node) => node.id);
}

function l2OrderKeysForParent(
  parentId: string,
  categories: CategoryNode[],
): string[] {
  return categories
    .filter((node) => node.level === 2 && node.parent_id === parentId)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((node) => node.id);
}

function resolveL1Id(row: ExpenseRecord, categories: CategoryNode[]): string {
  const node = categories.find((category) => category.id === row.category_node_id);
  if (node?.level === 2 && node.parent_id) return node.parent_id;
  return row.category_node_id;
}

function isDirectL1Assignment(
  row: ExpenseRecord,
  categories: CategoryNode[],
): boolean {
  const node = categories.find((category) => category.id === row.category_node_id);
  if (node) return node.level === 1;
  return !row.category_l2_name;
}

function orderL2Groups(
  l2Map: Map<string, ExpenseL2Group>,
  l1Id: string,
  categories: CategoryNode[],
): ExpenseL2Group[] {
  const ordered: ExpenseL2Group[] = [];
  const seen = new Set<string>();

  for (const l2Id of l2OrderKeysForParent(l1Id, categories)) {
    const group = l2Map.get(l2Id);
    if (group) {
      ordered.push(group);
      seen.add(l2Id);
    }
  }

  const remaining = [...l2Map.values()]
    .filter((group) => !seen.has(group.key))
    .sort((a, b) => a.label.localeCompare(b.label));

  return [...ordered, ...remaining];
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
    .sort((a, b) => {
      const aUnknown = isUnknownCategoryId(a.key, categories);
      const bUnknown = isUnknownCategoryId(b.key, categories);
      if (aUnknown && !bUnknown) return 1;
      if (bUnknown && !aUnknown) return -1;
      return a.label.localeCompare(b.label);
    });

  return [...ordered, ...remaining];
}

export function groupExpensesByL1Category(
  rows: ExpenseRecord[],
  categories: CategoryNode[],
): ExpenseL1Group[] {
  type L1Accumulator = {
    key: string;
    label: string;
    total: number;
    itemCount: number;
    l2Map: Map<string, ExpenseL2Group>;
    directItems: ExpenseRecord[];
  };

  const l1Map = new Map<string, L1Accumulator>();

  for (const row of rows) {
    const l1Id = resolveL1Id(row, categories);
    let l1Acc = l1Map.get(l1Id);
    if (!l1Acc) {
      const l1Node = categories.find((category) => category.id === l1Id);
      l1Acc = {
        key: l1Id,
        label:
          l1Node?.name_ja ??
          row.category_l1_name ??
          row.category_name_ja ??
          "—",
        total: 0,
        itemCount: 0,
        l2Map: new Map(),
        directItems: [],
      };
      l1Map.set(l1Id, l1Acc);
    }

    const amount = Number(row.amount);
    l1Acc.total += amount;
    l1Acc.itemCount += 1;

    if (isDirectL1Assignment(row, categories)) {
      l1Acc.directItems.push(row);
    } else {
      const l2Id = row.category_node_id;
      let l2Group = l1Acc.l2Map.get(l2Id);
      if (!l2Group) {
        const l2Node = categories.find((category) => category.id === l2Id);
        l2Group = {
          key: l2Id,
          label: l2Node?.name_ja ?? row.category_l2_name ?? "—",
          total: 0,
          items: [],
        };
        l1Acc.l2Map.set(l2Id, l2Group);
      }
      l2Group.total += amount;
      l2Group.items.push(row);
    }
  }

  const ordered: ExpenseL1Group[] = [];
  const seen = new Set<string>();

  for (const l1Id of l1OrderKeys(categories)) {
    const acc = l1Map.get(l1Id);
    if (!acc) continue;
    seen.add(l1Id);
    ordered.push({
      key: acc.key,
      label: acc.label,
      total: acc.total,
      itemCount: acc.itemCount,
      l2Groups: orderL2Groups(acc.l2Map, l1Id, categories),
      directItems: acc.directItems,
    });
  }

  const remaining = [...l1Map.values()]
    .filter((acc) => !seen.has(acc.key))
    .sort((a, b) => {
      const aUnknown = isUnknownCategoryId(a.key, categories);
      const bUnknown = isUnknownCategoryId(b.key, categories);
      if (aUnknown && !bUnknown) return 1;
      if (bUnknown && !aUnknown) return -1;
      return a.label.localeCompare(b.label);
    })
    .map((acc) => ({
      key: acc.key,
      label: acc.label,
      total: acc.total,
      itemCount: acc.itemCount,
      l2Groups: orderL2Groups(acc.l2Map, acc.key, categories),
      directItems: acc.directItems,
    }));

  return [...ordered, ...remaining];
}
