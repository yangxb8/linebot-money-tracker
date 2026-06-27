"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { ExpenseCategoryTag } from "@/components/expenses/ExpenseCategoryTag";
import { ExpenseForm } from "@/components/expenses/ExpenseForm";
import { FiscalMonthNavigator } from "@/components/expenses/FiscalMonthNavigator";
import { PAGE_SIZE } from "@/lib/dashboard/format";
import type { TenantOption } from "@/lib/dashboard/tenants";
import { fetchCategories } from "@/lib/categories/client";
import type { CategoryNode } from "@/lib/categories/types";
import {
  currentBudgetMonthJst,
  fiscalPeriodEnd,
  formatYen,
} from "@/lib/budget/format";
import {
  deleteExpense,
  fetchExpenseFiscalMonths,
  fetchExpensesForMonth,
} from "@/lib/expenses/client";
import type { ExpenseRecord, FiscalMonthOption } from "@/lib/expenses/types";
import { fetchTenantSettings } from "@/lib/settings/client";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  tenant: TenantOption;
  isNewUser?: boolean;
};

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function ExpenseList({ tenant, isNewUser }: Props) {
  const { t, locale } = useLanguage();
  const [fiscalStartDay, setFiscalStartDay] = useState(1);
  const [budgetMonth, setBudgetMonth] = useState(() => currentBudgetMonthJst());
  const [availableMonths, setAvailableMonths] = useState<FiscalMonthOption[]>([]);
  const [rows, setRows] = useState<ExpenseRecord[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ExpenseRecord | null>(null);
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const loadingMoreRef = useRef(false);

  const fmt = (amount: number) => formatYen(amount, locale as Locale);
  const monthMeta = availableMonths.find((month) => month.budget_month === budgetMonth);
  const monthTotal =
    monthMeta?.total_amount ??
    rows.reduce((sum, row) => sum + Number(row.amount), 0);

  const loadMonths = useCallback(async () => {
    const months = await fetchExpenseFiscalMonths(tenant);
    setAvailableMonths(months);
    return months;
  }, [tenant]);

  const loadPage = useCallback(
    async (nextOffset: number, append: boolean) => {
      if (append && loadingMoreRef.current) return;

      if (append) {
        loadingMoreRef.current = true;
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      setError(null);

      try {
        const page = await fetchExpensesForMonth(tenant, budgetMonth, nextOffset);
        setRows((prev) => (append ? [...prev, ...page] : page));
        setOffset(nextOffset + page.length);
        setHasMore(page.length === PAGE_SIZE);
      } catch {
        setError("fetch_failed");
      } finally {
        setLoading(false);
        setLoadingMore(false);
        loadingMoreRef.current = false;
      }
    },
    [tenant, budgetMonth],
  );

  const refresh = useCallback(async () => {
    setRows([]);
    setOffset(0);
    setHasMore(true);
    await loadMonths();
    await loadPage(0, false);
  }, [loadMonths, loadPage]);

  useEffect(() => {
    let cancelled = false;
    void fetchTenantSettings(tenant)
      .then((settings) => {
        if (cancelled) return;
        setFiscalStartDay(settings.fiscal_start_day);
        setBudgetMonth(currentBudgetMonthJst(settings.fiscal_start_day));
      })
      .catch(() => {
        if (!cancelled) {
          setFiscalStartDay(1);
          setBudgetMonth(currentBudgetMonthJst());
        }
      });
    return () => {
      cancelled = true;
    };
  }, [tenant]);

  useEffect(() => {
    let cancelled = false;
    void fetchCategories(tenant)
      .then((data) => {
        if (!cancelled) setCategories(data.nodes);
      })
      .catch(() => {
        if (!cancelled) setCategories([]);
      });
    return () => {
      cancelled = true;
    };
  }, [tenant]);

  useEffect(() => {
    setRows([]);
    setOffset(0);
    setHasMore(true);
    void loadPage(0, false);
  }, [loadPage]);

  useEffect(() => {
    void loadMonths().catch(() => {
      setError("fetch_failed");
    });
  }, [loadMonths]);

  useEffect(() => {
    if (!hasMore || loading || loadingMore) return;

    const sentinel = sentinelRef.current;
    if (!sentinel) return;

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

  function openEdit(expense: ExpenseRecord) {
    setEditing(expense);
    setFormOpen(true);
  }

  function handleExpenseUpdated(updated: ExpenseRecord) {
    setRows((prev) =>
      prev.map((row) => (row.id === updated.id ? updated : row)),
    );
    setEditing((prev) => (prev?.id === updated.id ? updated : prev));
  }

  async function handleDelete(expense: ExpenseRecord) {
    if (!window.confirm(t("expenseDeleteConfirm"))) return;
    setBusyId(expense.id);
    try {
      await deleteExpense(expense.id);
      await refresh();
    } catch {
      setError("action_failed");
    } finally {
      setBusyId(null);
    }
  }

  const defaultExpenseDate = (() => {
    const today = new Date().toISOString().slice(0, 10);
    const periodEnd = fiscalPeriodEnd(budgetMonth);
    if (today >= budgetMonth && today <= periodEnd) return today;
    return budgetMonth;
  })();

  return (
    <div className="space-y-4">
      <FiscalMonthNavigator
        budgetMonth={budgetMonth}
        fiscalStartDay={fiscalStartDay}
        availableMonths={availableMonths}
        onChange={setBudgetMonth}
      />

      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-gray-600">
          {t("expenseMonthTotal")}: {fmt(monthTotal)}
        </p>
        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
          className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm font-medium text-white"
        >
          {t("expenseAdd")}
        </button>
      </div>

      {loading ? (
        <p className="text-center text-sm text-gray-500 py-8">{t("loading")}</p>
      ) : error ? (
        <div className="text-center py-8 space-y-3">
          <p className="text-sm text-red-600">{t("errorGeneric")}</p>
          <button
            type="button"
            className="text-sm text-green-700 underline"
            onClick={() => void refresh()}
          >
            {t("retry")}
          </button>
        </div>
      ) : rows.length === 0 ? (
        <p className="text-center text-sm text-gray-500 py-8 px-4">
          {isNewUser ? t("emptyExpensesNewUser") : t("emptyExpensesMonth")}
        </p>
      ) : (
        <div className="space-y-3">
          <ul className="divide-y divide-gray-100 rounded-xl border border-gray-100 bg-white shadow-sm">
            {rows.map((row) => (
              <li
                key={row.id}
                role="button"
                tabIndex={busyId === row.id ? -1 : 0}
                onClick={() => {
                  if (busyId === row.id) return;
                  openEdit(row);
                }}
                onKeyDown={(event) => {
                  if (busyId === row.id) return;
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openEdit(row);
                  }
                }}
                className="px-4 py-3 text-left transition-colors hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-gray-400 disabled:opacity-60"
              >
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
                    {fmt(Number(row.amount))}
                  </p>
                </div>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <ExpenseCategoryTag
                    expense={row}
                    categories={categories}
                    disabled={busyId === row.id}
                    onUpdated={handleExpenseUpdated}
                    onError={() => setError("action_failed")}
                  />
                  <button
                    type="button"
                    disabled={busyId === row.id}
                    onClick={(event) => {
                      event.stopPropagation();
                      void handleDelete(row);
                    }}
                    className="text-xs text-red-600 underline"
                  >
                    {t("delete")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {hasMore ? (
            <p
              ref={sentinelRef}
              className="text-center text-xs text-gray-400 py-4"
              aria-live="polite"
            >
              {loadingMore ? t("loading") : t("pullToLoadMore")}
            </p>
          ) : null}
        </div>
      )}

      {formOpen ? (
        <ExpenseForm
          tenant={tenant}
          expense={editing}
          defaultDate={defaultExpenseDate}
          onClose={() => {
            setFormOpen(false);
            setEditing(null);
          }}
          onSaved={() => void refresh()}
        />
      ) : null}
    </div>
  );
}
