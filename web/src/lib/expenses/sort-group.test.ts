import { describe, expect, it } from "vitest";
import type { CategoryNode } from "@/lib/categories/types";
import type { ExpenseRecord } from "@/lib/expenses/types";
import {
  compareExpenses,
  groupExpensesByCategory,
  groupExpensesByL1Category,
  parseExpenseListSort,
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
    merchant_display: null,
    created_at: "2026-06-01T00:00:00.000Z",
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

describe("parseExpenseListSort", () => {
  it("defaults to date descending", () => {
    expect(parseExpenseListSort(null, null)).toEqual({
      field: "date",
      dir: "desc",
    });
  });

  it("parses amount ascending", () => {
    expect(parseExpenseListSort("amount", "asc")).toEqual({
      field: "amount",
      dir: "asc",
    });
  });

  it("falls back for invalid values", () => {
    expect(parseExpenseListSort("invalid", "sideways")).toEqual({
      field: "date",
      dir: "desc",
    });
  });
});

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

  it("sorts same-day expenses by created_at for newest first", () => {
    const rows = [
      expense({
        id: "older-id",
        expense_date: "2026-06-01",
        amount: 100,
        created_at: "2026-06-01T09:00:00.000Z",
      }),
      expense({
        id: "newer-id",
        expense_date: "2026-06-01",
        amount: 200,
        created_at: "2026-06-01T15:00:00.000Z",
      }),
    ];
    expect(sortExpenses(rows, "date", "desc").map((row) => row.id)).toEqual([
      "newer-id",
      "older-id",
    ]);
  });

  it("sorts same-day expenses by created_at for oldest first", () => {
    const rows = [
      expense({
        id: "newer-id",
        expense_date: "2026-06-01",
        amount: 200,
        created_at: "2026-06-01T15:00:00.000Z",
      }),
      expense({
        id: "older-id",
        expense_date: "2026-06-01",
        amount: 100,
        created_at: "2026-06-01T09:00:00.000Z",
      }),
    ];
    expect(sortExpenses(rows, "date", "asc").map((row) => row.id)).toEqual([
      "older-id",
      "newer-id",
    ]);
  });
});

describe("compareExpenses", () => {
  it("uses created_at as tiebreaker for same date", () => {
    const earlier = expense({
      id: "z",
      expense_date: "2026-06-01",
      amount: 100,
      created_at: "2026-06-01T09:00:00.000Z",
    });
    const later = expense({
      id: "a",
      expense_date: "2026-06-01",
      amount: 100,
      created_at: "2026-06-01T15:00:00.000Z",
    });
    expect(compareExpenses(earlier, later, "date", "asc")).toBeLessThan(0);
    expect(compareExpenses(earlier, later, "date", "desc")).toBeGreaterThan(0);
  });

  it("falls back to id when date and created_at match", () => {
    const a = expense({
      id: "a",
      expense_date: "2026-06-01",
      amount: 100,
      created_at: "2026-06-01T12:00:00.000Z",
    });
    const b = expense({
      id: "b",
      expense_date: "2026-06-01",
      amount: 100,
      created_at: "2026-06-01T12:00:00.000Z",
    });
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

  it("sorts unknown category last among orphan groups outside the tree order", () => {
    const rows = [
      expense({
        id: "o",
        expense_date: "2026-06-01",
        amount: 10,
        category_node_id: "cat-orphan-unknown",
        category_l1_name: "不明",
      }),
      expense({
        id: "x",
        expense_date: "2026-06-02",
        amount: 20,
        category_node_id: "cat-orphan-other",
        category_l1_name: "その他",
      }),
    ];
    const orphanCategories: CategoryNode[] = [
      {
        id: "cat-orphan-other",
        code: "other",
        name_ja: "その他",
        level: 1,
        parent_id: null,
        sort_order: 1,
        expense_count: 1,
        deletable: true,
      },
      {
        id: "cat-orphan-unknown",
        code: "unknown",
        name_ja: "不明",
        level: 1,
        parent_id: null,
        sort_order: 99,
        expense_count: 1,
        deletable: false,
      },
    ];

    const groups = groupExpensesByCategory(rows, orphanCategories);
    expect(groups.map((group) => group.key)).toEqual([
      "cat-orphan-other",
      "cat-orphan-unknown",
    ]);
  });
});

describe("groupExpensesByL1Category", () => {
  it("rolls L2 expenses into L1 totals", () => {
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
        category_node_id: "cat-groceries",
        category_l1_name: "食費",
        category_l2_name: "スーパー",
      }),
      expense({
        id: "c",
        expense_date: "2026-06-03",
        amount: 50,
        category_node_id: "cat-transport",
        category_l1_name: "交通",
      }),
    ];

    const groups = groupExpensesByL1Category(rows, categories);
    expect(groups).toHaveLength(2);
    expect(groups[0]).toMatchObject({
      key: "cat-food",
      label: "食費",
      total: 300,
      itemCount: 2,
    });
    expect(groups[0].l2Groups).toHaveLength(1);
    expect(groups[0].l2Groups[0]).toMatchObject({
      key: "cat-groceries",
      label: "スーパー",
      total: 200,
    });
    expect(groups[0].directItems.map((row) => row.id)).toEqual(["a"]);
    expect(groups[1]).toMatchObject({
      key: "cat-transport",
      total: 50,
      itemCount: 1,
    });
    expect(groups[1].directItems.map((row) => row.id)).toEqual(["c"]);
  });

  it("orders L1 groups by category tree sort_order", () => {
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

    const groups = groupExpensesByL1Category(rows, categories);
    expect(groups.map((group) => group.key)).toEqual(["cat-food", "cat-transport"]);
  });

  it("always sorts the unknown L1 category last", () => {
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
      }),
      expense({
        id: "c",
        expense_date: "2026-06-02",
        amount: 20,
        category_node_id: "cat-custom",
        category_l1_name: "カスタム",
      }),
      expense({
        id: "f",
        expense_date: "2026-06-03",
        amount: 30,
        category_node_id: "cat-food",
        category_l1_name: "食費",
      }),
    ];

    const groups = groupExpensesByL1Category(rows, withUnknownAndCustom);
    expect(groups.map((group) => group.key)).toEqual([
      "cat-food",
      "cat-custom",
      "cat-unknown",
    ]);
  });
});
