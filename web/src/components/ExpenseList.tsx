"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { fetchExpenses } from "@/lib/dashboard/expenses";
import {
  PAGE_SIZE,
  categoryLabel,
  type ExpenseRow,
} from "@/lib/dashboard/format";
import type { TenantOption } from "@/lib/dashboard/tenants";

type Props = {
  tenant: TenantOption;
  isNewUser?: boolean;
};

function formatJpy(amount: number): string {
  return `¥${amount.toLocaleString("ja-JP")}`;
}

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function ExpenseList({ tenant, isNewUser }: Props) {
  const { t } = useLanguage();
  const [rows, setRows] = useState<ExpenseRow[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const loadingMoreRef = useRef(false);

  const loadPage = useCallback(
    async (nextOffset: number, append: boolean) => {
      if (append && loadingMoreRef.current) {
        return;
      }

      if (append) {
        loadingMoreRef.current = true;
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const { rows: page, error: fetchError } = await fetchExpenses(
        tenant.tenantType,
        tenant.tenantId,
        nextOffset,
      );

      if (fetchError) {
        setError(fetchError);
        setLoading(false);
        setLoadingMore(false);
        loadingMoreRef.current = false;
        return;
      }

      setRows((prev) => (append ? [...prev, ...page] : page));
      setOffset(nextOffset + page.length);
      setHasMore(page.length === PAGE_SIZE);
      setLoading(false);
      setLoadingMore(false);
      loadingMoreRef.current = false;
    },
    [tenant.tenantId, tenant.tenantType],
  );

  useEffect(() => {
    setRows([]);
    setOffset(0);
    setHasMore(true);
    void loadPage(0, false);
  }, [loadPage, tenant.tenantId, tenant.tenantType]);

  useEffect(() => {
    if (!hasMore || loading || loadingMore) {
      return;
    }

    const sentinel = sentinelRef.current;
    if (!sentinel) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          void loadPage(offset, true);
        }
      },
      { rootMargin: "120px" },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loading, loadingMore, loadPage, offset]);

  if (loading) {
    return (
      <p className="text-center text-sm text-gray-500 py-8">{t("loading")}</p>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 space-y-3">
        <p className="text-sm text-red-600">{t("errorGeneric")}</p>
        <button
          type="button"
          className="text-sm text-green-700 underline"
          onClick={() => void loadPage(0, false)}
        >
          {t("retry")}
        </button>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <p className="text-center text-sm text-gray-500 py-8 px-4">
        {isNewUser ? t("emptyExpensesNewUser") : t("emptyExpenses")}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <ul className="divide-y divide-gray-100 rounded-xl border border-gray-100 bg-white shadow-sm">
        {rows.map((row) => (
          <li key={row.id} className="px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900 break-words line-clamp-3">
                  {row.description}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {formatDate(row.expense_date)}
                </p>
              </div>
              <p className="text-sm font-semibold text-gray-900 shrink-0">
                {formatJpy(Number(row.amount))}
              </p>
            </div>
            <span className="inline-block mt-2 text-xs rounded-full bg-gray-100 px-2 py-0.5 text-gray-600">
              {categoryLabel(row)}
            </span>
          </li>
        ))}
      </ul>
      {hasMore && (
        <p
          ref={sentinelRef}
          className="text-center text-xs text-gray-400 py-4"
          aria-live="polite"
        >
          {loadingMore ? t("loading") : t("pullToLoadMore")}
        </p>
      )}
    </div>
  );
}
