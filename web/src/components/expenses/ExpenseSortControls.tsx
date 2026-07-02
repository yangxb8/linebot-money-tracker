"use client";

import type { ExpenseSortDir, ExpenseSortField } from "@/lib/expenses/sort-group";

type Props = {
  sortField: ExpenseSortField;
  sortDir: ExpenseSortDir;
  labels: {
    sortBy: string;
    sortDate: string;
    sortAmount: string;
    dateLateToEarly: string;
    dateEarlyToLate: string;
    amountLargeToSmall: string;
    amountSmallToLarge: string;
  };
  onSortFieldChange: (value: ExpenseSortField) => void;
  onSortDirChange: (value: ExpenseSortDir) => void;
};

export function ExpenseSortControls({
  sortField,
  sortDir,
  labels,
  onSortFieldChange,
  onSortDirChange,
}: Props) {
  const ascLabel =
    sortField === "date" ? labels.dateEarlyToLate : labels.amountSmallToLarge;
  const descLabel =
    sortField === "date" ? labels.dateLateToEarly : labels.amountLargeToSmall;

  return (
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
  );
}
