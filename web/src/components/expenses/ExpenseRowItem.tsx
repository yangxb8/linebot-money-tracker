"use client";

import { ExpenseCategoryTag } from "@/components/expenses/ExpenseCategoryTag";
import { ExpenseMerchantTag } from "@/components/expenses/ExpenseMerchantTag";
import { useLanguage } from "@/components/LanguageProvider";
import type { CategoryNode } from "@/lib/categories/types";
import type { ExpenseRecord } from "@/lib/expenses/types";

type Props = {
  row: ExpenseRecord;
  categories: CategoryNode[];
  busyId: string | null;
  formatAmount: (amount: number) => string;
  formatDate: (date: string) => string;
  deleteLabel: string;
  onEdit: (expense: ExpenseRecord) => void;
  onDelete: (expense: ExpenseRecord) => void;
  onUpdated: (expense: ExpenseRecord) => void;
  onError: () => void;
};

export function ExpenseRowItem({
  row,
  categories,
  busyId,
  formatAmount,
  formatDate,
  deleteLabel,
  onEdit,
  onDelete,
  onUpdated,
  onError,
}: Props) {
  const { t } = useLanguage();
  const disabled = busyId === row.id;

  return (
    <li
      role="button"
      tabIndex={disabled ? -1 : 0}
      onClick={() => {
        if (disabled) return;
        onEdit(row);
      }}
      onKeyDown={(event) => {
        if (disabled) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onEdit(row);
        }
      }}
      className="px-4 py-3 text-left transition-colors hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-gray-400 disabled:opacity-60"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 break-words line-clamp-3">
            {row.description}
          </p>
          <p className="text-xs text-gray-500 mt-1">{formatDate(row.expense_date)}</p>
        </div>
        <p className="text-sm font-semibold text-gray-900 shrink-0">
          {formatAmount(Number(row.amount))}
        </p>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
          <ExpenseCategoryTag
            expense={row}
            categories={categories}
            disabled={disabled}
            onUpdated={onUpdated}
            onError={onError}
          />
          {row.merchant_display ? (
            <ExpenseMerchantTag label={row.merchant_display} />
          ) : null}
          {row.wish_list_item_id ? (
            <span className="inline-block max-w-full truncate rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
              {t("wishListTag")}
            </span>
          ) : null}
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={(event) => {
            event.stopPropagation();
            onDelete(row);
          }}
          className="text-xs text-red-600 underline"
        >
          {deleteLabel}
        </button>
      </div>
    </li>
  );
}
