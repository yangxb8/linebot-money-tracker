import { fiscalPeriodEnd, fiscalPeriodStartForDate } from "@/lib/budget/format";
import type { ExpenseRecord, FiscalMonthOption } from "@/lib/expenses/types";

export function expenseInBudgetMonth(
  expenseDate: string,
  budgetMonth: string,
): boolean {
  const periodEnd = fiscalPeriodEnd(budgetMonth);
  return expenseDate >= budgetMonth && expenseDate <= periodEnd;
}

export function budgetMonthForExpense(
  expenseDate: string,
  fiscalStartDay: number,
): string {
  const [year, month, day] = expenseDate.split("-").map(Number);
  return fiscalPeriodStartForDate(year, month, day, fiscalStartDay);
}

function compareExpenseDesc(a: ExpenseRecord, b: ExpenseRecord): number {
  return b.expense_date.localeCompare(a.expense_date);
}

export function upsertExpense(
  rows: ExpenseRecord[],
  expense: ExpenseRecord,
): ExpenseRecord[] {
  const next = [...rows.filter((row) => row.id !== expense.id), expense];
  next.sort(compareExpenseDesc);
  return next;
}

export function adjustMonthMeta(
  months: FiscalMonthOption[],
  budgetMonth: string,
  deltaAmount: number,
  deltaCount: number,
): FiscalMonthOption[] {
  const existing = months.find((month) => month.budget_month === budgetMonth);
  if (existing) {
    return months.map((month) =>
      month.budget_month === budgetMonth
        ? {
            ...month,
            total_amount: month.total_amount + deltaAmount,
            expense_count: Math.max(0, month.expense_count + deltaCount),
          }
        : month,
    );
  }

  if (deltaCount <= 0) return months;

  return [
    ...months,
    {
      budget_month: budgetMonth,
      expense_count: deltaCount,
      total_amount: deltaAmount,
    },
  ].sort((a, b) => b.budget_month.localeCompare(a.budget_month));
}

export type ExpenseListMutation = {
  rows: ExpenseRecord[];
  offsetDelta: number;
  monthMeta: FiscalMonthOption[];
};

export function applyExpenseCreated(
  rows: ExpenseRecord[],
  months: FiscalMonthOption[],
  created: ExpenseRecord,
  viewedBudgetMonth: string,
  fiscalStartDay: number,
): ExpenseListMutation {
  const createdMonth = budgetMonthForExpense(created.expense_date, fiscalStartDay);
  let nextRows = rows;
  let offsetDelta = 0;

  if (expenseInBudgetMonth(created.expense_date, viewedBudgetMonth)) {
    nextRows = upsertExpense(rows, created);
    offsetDelta = 1;
  }

  return {
    rows: nextRows,
    offsetDelta,
    monthMeta: adjustMonthMeta(months, createdMonth, created.amount, 1),
  };
}

export function applyExpenseUpdated(
  rows: ExpenseRecord[],
  months: FiscalMonthOption[],
  updated: ExpenseRecord,
  previous: ExpenseRecord,
  viewedBudgetMonth: string,
  fiscalStartDay: number,
): ExpenseListMutation {
  const wasInView = expenseInBudgetMonth(previous.expense_date, viewedBudgetMonth);
  const nowInView = expenseInBudgetMonth(updated.expense_date, viewedBudgetMonth);
  const oldMonth = budgetMonthForExpense(previous.expense_date, fiscalStartDay);
  const newMonth = budgetMonthForExpense(updated.expense_date, fiscalStartDay);

  let nextRows = rows;
  let offsetDelta = 0;

  if (wasInView && nowInView) {
    nextRows = upsertExpense(rows, updated);
  } else if (wasInView && !nowInView) {
    nextRows = rows.filter((row) => row.id !== updated.id);
    offsetDelta = -1;
  } else if (!wasInView && nowInView) {
    nextRows = upsertExpense(rows, updated);
    offsetDelta = 1;
  }

  let monthMeta = months;
  if (oldMonth === newMonth) {
    if (wasInView) {
      monthMeta = adjustMonthMeta(
        months,
        viewedBudgetMonth,
        updated.amount - previous.amount,
        0,
      );
    }
  } else {
    monthMeta = adjustMonthMeta(months, oldMonth, -previous.amount, -1);
    monthMeta = adjustMonthMeta(monthMeta, newMonth, updated.amount, 1);
  }

  return { rows: nextRows, offsetDelta, monthMeta };
}

export function applyExpenseDeleted(
  rows: ExpenseRecord[],
  months: FiscalMonthOption[],
  deleted: ExpenseRecord,
  viewedBudgetMonth: string,
  fiscalStartDay: number,
): ExpenseListMutation {
  const deletedMonth = budgetMonthForExpense(deleted.expense_date, fiscalStartDay);
  let nextRows = rows;
  let offsetDelta = 0;

  if (expenseInBudgetMonth(deleted.expense_date, viewedBudgetMonth)) {
    nextRows = rows.filter((row) => row.id !== deleted.id);
    offsetDelta = -1;
  }

  return {
    rows: nextRows,
    offsetDelta,
    monthMeta: adjustMonthMeta(months, deletedMonth, -deleted.amount, -1),
  };
}
