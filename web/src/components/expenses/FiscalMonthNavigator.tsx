"use client";

import { useLanguage } from "@/components/LanguageProvider";
import {
  currentBudgetMonthJst,
  formatBudgetPeriodLabel,
  shiftBudgetMonth,
} from "@/lib/budget/format";
import type { FiscalMonthOption } from "@/lib/expenses/types";

type Props = {
  budgetMonth: string;
  fiscalStartDay: number;
  availableMonths: FiscalMonthOption[];
  onChange: (budgetMonth: string) => void;
};

export function FiscalMonthNavigator({
  budgetMonth,
  fiscalStartDay,
  availableMonths,
  onChange,
}: Props) {
  const { t } = useLanguage();
  const currentMonth = currentBudgetMonthJst(fiscalStartDay);
  const canGoNext = budgetMonth < currentMonth;

  const selectOptions = [...availableMonths];
  if (!selectOptions.some((month) => month.budget_month === budgetMonth)) {
    selectOptions.unshift({
      budget_month: budgetMonth,
      expense_count: 0,
      total_amount: 0,
    });
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        aria-label={t("expensePreviousMonth")}
        className="rounded border border-gray-200 px-2 py-1 text-sm"
        onClick={() => onChange(shiftBudgetMonth(budgetMonth, -1))}
      >
        ‹
      </button>

      <select
        aria-label={t("expenseSelectMonth")}
        value={budgetMonth}
        onChange={(event) => onChange(event.target.value)}
        className="min-w-0 flex-1 rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm font-medium text-gray-800"
      >
        {selectOptions.map((month) => (
          <option key={month.budget_month} value={month.budget_month}>
            {formatBudgetPeriodLabel(
              month.budget_month,
              undefined,
              fiscalStartDay,
            )}
            {month.expense_count > 0 ? ` (${month.expense_count})` : ""}
          </option>
        ))}
      </select>

      <button
        type="button"
        aria-label={t("expenseNextMonth")}
        className="rounded border border-gray-200 px-2 py-1 text-sm disabled:opacity-40"
        disabled={!canGoNext}
        onClick={() => onChange(shiftBudgetMonth(budgetMonth, 1))}
      >
        ›
      </button>
    </div>
  );
}
