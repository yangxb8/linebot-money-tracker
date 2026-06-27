"use client";

import type { ExpenseSortDir, ExpenseSortField } from "@/lib/expenses/sort-group";

type Props = {
  groupByCategory: boolean;
  sortField: ExpenseSortField;
  sortDir: ExpenseSortDir;
  labels: {
    groupByCategory: string;
    sortBy: string;
    sortDate: string;
    sortAmount: string;
    dateLateToEarly: string;
    dateEarlyToLate: string;
    amountLargeToSmall: string;
    amountSmallToLarge: string;
  };
  onGroupByCategoryChange: (value: boolean) => void;
  onSortFieldChange: (value: ExpenseSortField) => void;
  onSortDirChange: (value: ExpenseSortDir) => void;
};

export function ExpenseListControls({
  groupByCategory,
  sortField,
  sortDir,
  labels,
  onGroupByCategoryChange,
  onSortFieldChange,
  onSortDirChange,
}: Props) {
  const ascLabel =
    sortField === "date" ? labels.dateEarlyToLate : labels.amountSmallToLarge;
  const descLabel =
    sortField === "date" ? labels.dateLateToEarly : labels.amountLargeToSmall;

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-100 bg-white px-3 py-2 shadow-sm">
      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={groupByCategory}
          onChange={(event) => onGroupByCategoryChange(event.target.checked)}
          className="rounded border-gray-300 text-gray-900 focus:ring-gray-500"
        />
        {labels.groupByCategory}
      </label>

      <div className="flex flex-wrap items-center gap-2 text-sm text-gray-700">
        <span>{labels.sortBy}</span>
        <select
          value={sortField}
          onChange={(event) =>
            onSortFieldChange(event.target.value as ExpenseSortField)
          }
          className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-sm"
        >
          <option value="date">{labels.sortDate}</option>
          <option value="amount">{labels.sortAmount}</option>
        </select>
        <select
          value={sortDir}
          onChange={(event) =>
            onSortDirChange(event.target.value as ExpenseSortDir)
          }
          className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-sm"
        >
          <option value="desc">{descLabel}</option>
          <option value="asc">{ascLabel}</option>
        </select>
      </div>
    </div>
  );
}
