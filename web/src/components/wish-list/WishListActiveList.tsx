"use client";

import { useLanguage } from "@/components/LanguageProvider";
import type {
  WishListItem,
  WishListSort,
} from "@/lib/wish-list/types";

type Props = {
  items: WishListItem[];
  loading: boolean;
  error: string | null;
  busyId: string | null;
  sort: WishListSort;
  onSortChange: (sort: WishListSort) => void;
  onRetry: () => void;
  onCreate: () => void;
  onMove: (item: WishListItem, direction: "up" | "down") => void;
  onEdit: (item: WishListItem) => void;
  onDelete: (item: WishListItem) => void;
  onExecute: (item: WishListItem) => void;
};

function formatAmount(amount: number) {
  return new Intl.NumberFormat("ja-JP", {
    style: "currency",
    currency: "JPY",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function WishListActiveList({
  items,
  loading,
  error,
  busyId,
  sort,
  onSortChange,
  onRetry,
  onCreate,
  onMove,
  onEdit,
  onDelete,
  onExecute,
}: Props) {
  const { t } = useLanguage();

  if (loading) {
    return (
      <p className="py-12 text-center text-sm text-gray-500">{t("loading")}</p>
    );
  }

  if (error) {
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
        <p className="text-sm text-gray-600">{t("wishListEmpty")}</p>
        <button
          type="button"
          onClick={onCreate}
          className="mt-4 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white"
        >
          {t("wishListAdd")}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <label className="text-sm font-medium text-gray-700">
          {t("expenseSortBy")}
        </label>
        <select
          value={sort}
          onChange={(event) => onSortChange(event.target.value as WishListSort)}
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700"
        >
          <option value="priority">{t("wishListSortPriority")}</option>
          <option value="created">{t("wishListSortCreated")}</option>
          <option value="price">{t("wishListSortPrice")}</option>
        </select>
      </div>

      <ul className="space-y-3">
        {items.map((item, index) => {
          const busy = busyId === item.id;
          const priorityControlsDisabled = sort !== "priority" || busy;
          return (
            <li
              key={item.id}
              className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="break-words text-sm font-semibold text-gray-900">
                    {item.name}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {item.category_name ?? t("periodicCategory")}
                  </p>
                </div>
                <p className="shrink-0 text-sm font-semibold text-gray-900">
                  {formatAmount(item.amount)}
                </p>
              </div>

              {item.product_url ? (
                <a
                  href={item.product_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block max-w-full truncate text-xs text-gray-600 underline"
                >
                  {item.product_url}
                </a>
              ) : null}

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex gap-1.5">
                  <button
                    type="button"
                    disabled={priorityControlsDisabled || index === 0}
                    onClick={() => onMove(item, "up")}
                    className="rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-700 disabled:opacity-40"
                  >
                    {t("wishListMoveUp")}
                  </button>
                  <button
                    type="button"
                    disabled={priorityControlsDisabled || index === items.length - 1}
                    onClick={() => onMove(item, "down")}
                    className="rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-700 disabled:opacity-40"
                  >
                    {t("wishListMoveDown")}
                  </button>
                </div>

                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onEdit(item)}
                    className="text-xs text-gray-600 underline disabled:opacity-40"
                  >
                    {t("edit")}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onDelete(item)}
                    className="text-xs text-red-600 underline disabled:opacity-40"
                  >
                    {t("delete")}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onExecute(item)}
                    className="rounded-lg bg-gray-900 px-3 py-1 text-xs font-medium text-white disabled:opacity-40"
                  >
                    {t("wishListExecute")}
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
