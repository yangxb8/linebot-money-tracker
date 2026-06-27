import { describe, expect, it } from "vitest";
import {
  applyExpenseCreated,
  applyExpenseDeleted,
  applyExpenseUpdated,
  expenseInBudgetMonth,
  upsertExpense,
} from "@/lib/expenses/list-mutations";
import type { ExpenseRecord, FiscalMonthOption } from "@/lib/expenses/types";

function expense(
  overrides: Partial<ExpenseRecord> & Pick<ExpenseRecord, "id" | "expense_date" | "amount">,
): ExpenseRecord {
  return {
    description: "Test",
    currency: "JPY",
    category_node_id: "cat-1",
    category_name_ja: "Food",
    category_l1_name: "Food",
    category_l2_name: null,
    logged_by_line_user_id: "u1",
    tenant_type: "personal",
    tenant_id: "t1",
    ...overrides,
  };
}

const months: FiscalMonthOption[] = [
  {
    budget_month: "2026-06-01",
    expense_count: 2,
    total_amount: 3000,
  },
];

describe("expense list mutations", () => {
  it("detects whether an expense belongs to the viewed month", () => {
    expect(expenseInBudgetMonth("2026-06-15", "2026-06-01")).toBe(true);
    expect(expenseInBudgetMonth("2026-05-31", "2026-06-01")).toBe(false);
  });

  it("inserts created expenses into the visible month only", () => {
    const rows = [expense({ id: "a", expense_date: "2026-06-10", amount: 1000 })];
    const result = applyExpenseCreated(
      rows,
      months,
      expense({ id: "b", expense_date: "2026-06-20", amount: 500 }),
      "2026-06-01",
      1,
    );

    expect(result.rows.map((row) => row.id)).toEqual(["b", "a"]);
    expect(result.offsetDelta).toBe(1);
    expect(result.monthMeta[0]?.expense_count).toBe(3);
    expect(result.monthMeta[0]?.total_amount).toBe(3500);
  });

  it("updates a visible expense in place and adjusts totals", () => {
    const rows = [
      expense({ id: "a", expense_date: "2026-06-20", amount: 1000 }),
      expense({ id: "b", expense_date: "2026-06-10", amount: 500 }),
    ];
    const previous = rows[0];
    const updated = expense({
      ...previous,
      description: "Updated",
      amount: 1500,
    });

    const result = applyExpenseUpdated(
      rows,
      months,
      updated,
      previous,
      "2026-06-01",
      1,
    );

    expect(result.rows[0]?.description).toBe("Updated");
    expect(result.rows[0]?.amount).toBe(1500);
    expect(result.monthMeta[0]?.total_amount).toBe(3500);
  });

  it("removes an expense moved out of the viewed month", () => {
    const rows = [expense({ id: "a", expense_date: "2026-06-10", amount: 1000 })];
    const previous = rows[0];
    const updated = expense({ ...previous, expense_date: "2026-05-15" });

    const result = applyExpenseUpdated(
      rows,
      months,
      updated,
      previous,
      "2026-06-01",
      1,
    );

    expect(result.rows).toHaveLength(0);
    expect(result.offsetDelta).toBe(-1);
    expect(result.monthMeta[0]?.expense_count).toBe(1);
    expect(result.monthMeta[0]?.total_amount).toBe(2000);
  });

  it("removes deleted expenses from the visible list", () => {
    const rows = [
      expense({ id: "a", expense_date: "2026-06-20", amount: 1000 }),
      expense({ id: "b", expense_date: "2026-06-10", amount: 500 }),
    ];
    const deleted = rows[0];

    const result = applyExpenseDeleted(rows, months, deleted, "2026-06-01", 1);

    expect(result.rows.map((row) => row.id)).toEqual(["b"]);
    expect(result.offsetDelta).toBe(-1);
    expect(result.monthMeta[0]?.expense_count).toBe(1);
    expect(result.monthMeta[0]?.total_amount).toBe(2000);
  });

  it("sorts expenses by date descending", () => {
    const rows = upsertExpense(
      [expense({ id: "a", expense_date: "2026-06-10", amount: 100 })],
      expense({ id: "b", expense_date: "2026-06-20", amount: 200 }),
    );

    expect(rows.map((row) => row.id)).toEqual(["b", "a"]);
  });
});
