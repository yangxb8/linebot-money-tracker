import { describe, expect, it } from "vitest";
import type { CategoryNode } from "@/lib/categories/types";
import type { ExpenseRecord } from "@/lib/expenses/types";
import {
  compareExpenses,
  groupExpensesByCategory,
  sortExpenses,
} from "@/lib/expenses/sort-group";

function expense(
  overrides: Partial<ExpenseRecord> & Pick<ExpenseRecord, "id" | "expense_date" | "amount">,
): ExpenseRecord {
  return {
    description: "Test",
    currency: "JPY",
    category_node_id: "cat-food",
    category_name_ja: "Food",
    category_l1_name: "Food",
    category_l2_name: null,
    logged_by_line_user_id: "u1",
    tenant_type: "personal",
    tenant_id: "t1",
    ...overrides,
  };
}

const categories: CategoryNode[] = [
  {
    id: "cat-food",
    code: "food",
    name_ja: "食費",
    level: 1,
    parent_id: null,
    sort_order: 1,
    expense_count: 1,
    deletable: true,
  },
  {
    id: "cat-transport",
    code: "transport",
    name_ja: "交通",
    level: 1,
    parent_id: null,
    sort_order: 2,
    expense_count: 1,
    deletable: true,
  },
  {
    id: "cat-groceries",
    code: "groceries",
    name_ja: "スーパー",
    level: 2,
    parent_id: "cat-food",
    sort_order: 1,
    expense_count: 1,
    deletable: true,
  },
];

describe("sortExpenses", () => {
  it("sorts by date descending", () => {
    const rows = [
      expense({ id: "a", expense_date: "2026-06-01", amount: 100 }),
      expense({ id: "b", expense_date: "2026-06-15", amount: 200 }),
    ];
    expect(sortExpenses(rows, "date", "desc").map((row) => row.id)).toEqual([
      "b",
      "a",
    ]);
  });

  it("sorts by date ascending", () => {
    const rows = [
      expense({ id: "a", expense_date: "2026-06-15", amount: 100 }),
      expense({ id: "b", expense_date: "2026-06-01", amount: 200 }),
    ];
    expect(sortExpenses(rows, "date", "asc").map((row) => row.id)).toEqual([
      "b",
      "a",
    ]);
  });

  it("sorts by amount descending", () => {
    const rows = [
      expense({ id: "a", expense_date: "2026-06-01", amount: 100 }),
      expense({ id: "b", expense_date: "2026-06-01", amount: 500 }),
    ];
    expect(sortExpenses(rows, "amount", "desc").map((row) => row.id)).toEqual([
      "b",
      "a",
    ]);
  });

  it("sorts by amount ascending", () => {
    const rows = [
      expense({ id: "a", expense_date: "2026-06-01", amount: 500 }),
      expense({ id: "b", expense_date: "2026-06-01", amount: 100 }),
    ];
    expect(sortExpenses(rows, "amount", "asc").map((row) => row.id)).toEqual([
      "b",
      "a",
    ]);
  });
});

describe("compareExpenses", () => {
  it("uses id as tiebreaker for same date", () => {
    const a = expense({ id: "a", expense_date: "2026-06-01", amount: 100 });
    const b = expense({ id: "b", expense_date: "2026-06-01", amount: 100 });
    expect(compareExpenses(a, b, "date", "asc")).toBeLessThan(0);
    expect(compareExpenses(a, b, "date", "desc")).toBeGreaterThan(0);
  });
});

describe("groupExpensesByCategory", () => {
  it("groups expenses and sums totals", () => {
    const rows = [
      expense({
        id: "a",
        expense_date: "2026-06-01",
        amount: 100,
        category_node_id: "cat-food",
        category_l1_name: "食費",
      }),
      expense({
        id: "b",
        expense_date: "2026-06-02",
        amount: 200,
        category_node_id: "cat-food",
        category_l1_name: "食費",
      }),
      expense({
        id: "c",
        expense_date: "2026-06-03",
        amount: 50,
        category_node_id: "cat-transport",
        category_l1_name: "交通",
      }),
    ];

    const groups = groupExpensesByCategory(rows, categories);
    expect(groups).toHaveLength(2);
    expect(groups[0]).toMatchObject({ key: "cat-food", total: 300, label: "食費" });
    expect(groups[0].items).toHaveLength(2);
    expect(groups[1]).toMatchObject({ key: "cat-transport", total: 50 });
  });

  it("orders groups by category tree sort_order", () => {
    const rows = [
      expense({
        id: "a",
        expense_date: "2026-06-01",
        amount: 50,
        category_node_id: "cat-transport",
        category_l1_name: "交通",
      }),
      expense({
        id: "b",
        expense_date: "2026-06-02",
        amount: 100,
        category_node_id: "cat-groceries",
        category_l1_name: "食費",
        category_l2_name: "スーパー",
      }),
    ];

    const groups = groupExpensesByCategory(rows, categories);
    expect(groups.map((group) => group.key)).toEqual([
      "cat-groceries",
      "cat-transport",
    ]);
  });

  it("always sorts the unknown L1 category last, even with custom categories after it", () => {
    const withUnknownAndCustom: CategoryNode[] = [
      ...categories,
      {
        id: "cat-unknown",
        code: "unknown",
        name_ja: "不明",
        level: 1,
        parent_id: null,
        sort_order: 99,
        expense_count: 0,
        deletable: false,
      },
      {
        id: "cat-custom",
        code: "custom.abc",
        name_ja: "カスタム",
        level: 1,
        parent_id: null,
        sort_order: 100,
        expense_count: 0,
        deletable: true,
      },
    ];
    const rows = [
      expense({
        id: "u",
        expense_date: "2026-06-01",
        amount: 10,
        category_node_id: "cat-unknown",
        category_l1_name: "不明",
        category_l2_name: null,
      }),
      expense({
        id: "c",
        expense_date: "2026-06-02",
        amount: 20,
        category_node_id: "cat-custom",
        category_l1_name: "カスタム",
        category_l2_name: null,
      }),
      expense({
        id: "f",
        expense_date: "2026-06-03",
        amount: 30,
        category_node_id: "cat-food",
        category_l1_name: "食費",
      }),
    ];

    const groups = groupExpensesByCategory(rows, withUnknownAndCustom);
    expect(groups.map((group) => group.key)).toEqual([
      "cat-food",
      "cat-custom",
      "cat-unknown",
    ]);
  });
});
