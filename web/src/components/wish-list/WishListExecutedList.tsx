"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";
import type { WishListItem } from "@/lib/wish-list/types";

type Props = {
  items: WishListItem[];
  loading: boolean;
  loadError: string | null;
  onRetry: () => void;
};

function formatAmount(amount: number) {
  return new Intl.NumberFormat("ja-JP", {
    style: "currency",
    currency: "JPY",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function WishListExecutedList({
  items,
  loading,
  loadError,
  onRetry,
}: Props) {
  const { t } = useLanguage();

  if (loading) {
    return (
      <p className="py-12 text-center text-sm text-gray-500">{t("loading")}</p>
    );
  }

  if (loadError) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-600">{t("errorGeneric")}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 text-sm font-medium text-gray-900 underline"
        >
          {t("retry")}
        </button>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 bg-white p-8 text-center">
        <p className="text-sm text-gray-600">{t("wishListEmptyExecuted")}</p>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => {
        const expense = item.expense;
        return (
          <li
            key={item.id}
            className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="break-words text-sm font-semibold text-gray-900">
                  {expense?.description ?? item.name}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  {expense?.expense_date ?? "-"} ·{" "}
                  {expense?.category_name ?? item.category_name ?? t("periodicCategory")}
                </p>
              </div>
              <p className="shrink-0 text-sm font-semibold text-gray-900">
                {formatAmount(expense?.amount ?? item.amount)}
              </p>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                {t("wishListTag")}
              </span>
              <Link
                href="/dashboard"
                className="text-xs font-medium text-gray-700 underline"
              >
                {t("wishListExecutedLink")}
              </Link>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
