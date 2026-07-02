"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { ExpenseForm } from "@/components/expenses/ExpenseForm";
import { ExpenseGroupList } from "@/components/expenses/ExpenseGroupList";
import { ExpenseListControls } from "@/components/expenses/ExpenseListControls";
import { ExpenseRowItem } from "@/components/expenses/ExpenseRowItem";
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
  fetchAllExpensesForMonth,
  fetchExpenseFiscalMonths,
  fetchExpensesForMonth,
} from "@/lib/expenses/client";
import {
  applyExpenseCreated,
  applyExpenseDeleted,
  applyExpenseUpdated,
} from "@/lib/expenses/list-mutations";
import {
  groupExpensesByL1Category,
  sortExpenses,
  type ExpenseSortDir,
  type ExpenseSortField,
} from "@/lib/expenses/sort-group";
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
  const [loadingAll, setLoadingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ExpenseRecord | null>(null);
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [groupByCategory, setGroupByCategory] = useState(false);
  const [sortField, setSortField] = useState<ExpenseSortField>("date");
  const [sortDir, setSortDir] = useState<ExpenseSortDir>("desc");
  const sentinelRef = useRef<HTMLDivElement>(null);
  const loadingMoreRef = useRef(false);

  const fmt = (amount: number) => formatYen(amount, locale as Locale);
  const monthMeta = availableMonths.find((month) => month.budget_month === budgetMonth);
  const monthTotal =
    monthMeta?.total_amount ??
    rows.reduce((sum, row) => sum + Number(row.amount), 0);

  const sortedRows = useMemo(
    () => sortExpenses(rows, sortField, sortDir),
    [rows, sortField, sortDir],
  );

  const l1Groups = useMemo(() => {
    const grouped = groupExpensesByL1Category(rows, categories);
    return grouped.map((group) => ({
      ...group,
      directItems: sortExpenses(group.directItems, sortField, sortDir),
      l2Groups: group.l2Groups.map((l2Group) => ({
        ...l2Group,
        items: sortExpenses(l2Group.items, sortField, sortDir),
      })),
    }));
  }, [rows, categories, sortField, sortDir]);

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
    if (!groupByCategory || !hasMore || loading || loadingMore) return;

    let cancelled = false;
    setLoadingAll(true);
    setError(null);

    void fetchAllExpensesForMonth(tenant, budgetMonth, PAGE_SIZE)
      .then((all) => {
        if (cancelled) return;
        setRows(all);
        setOffset(all.length);
        setHasMore(false);
      })
      .catch(() => {
        if (!cancelled) setError("fetch_failed");
      })
      .finally(() => {
        if (!cancelled) setLoadingAll(false);
      });

    return () => {
      cancelled = true;
    };
  }, [groupByCategory, hasMore, loading, loadingMore, tenant, budgetMonth]);

  useEffect(() => {
    if (groupByCategory || !hasMore || loading || loadingMore) return;

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
  }, [groupByCategory, hasMore, loading, loadingMore, loadPage, offset]);

  function handleGroupByCategoryChange(enabled: boolean) {
    setGroupByCategory(enabled);
  }

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

  function handleExpenseSaved(saved: ExpenseRecord) {
    if (editing) {
      const mutation = applyExpenseUpdated(
        rows,
        availableMonths,
        saved,
        editing,
        budgetMonth,
        fiscalStartDay,
      );
      setRows(mutation.rows);
      setAvailableMonths(mutation.monthMeta);
      setOffset((prev) => Math.max(0, prev + mutation.offsetDelta));
      setEditing(null);
      return;
    }

    const mutation = applyExpenseCreated(
      rows,
      availableMonths,
      saved,
      budgetMonth,
      fiscalStartDay,
    );
    setRows(mutation.rows);
    setAvailableMonths(mutation.monthMeta);
    setOffset((prev) => prev + mutation.offsetDelta);
  }

  async function handleDelete(expense: ExpenseRecord) {
    if (!window.confirm(t("expenseDeleteConfirm"))) return;
    setBusyId(expense.id);
    try {
      await deleteExpense(expense.id);
      const mutation = applyExpenseDeleted(
        rows,
        availableMonths,
        expense,
        budgetMonth,
        fiscalStartDay,
      );
      setRows(mutation.rows);
      setAvailableMonths(mutation.monthMeta);
      setOffset((prev) => Math.max(0, prev + mutation.offsetDelta));
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

  const rowProps = {
    categories,
    busyId,
    formatAmount: fmt,
    formatDate,
    deleteLabel: t("delete"),
    onEdit: openEdit,
    onDelete: (expense: ExpenseRecord) => void handleDelete(expense),
    onUpdated: handleExpenseUpdated,
    onError: () => setError("action_failed"),
  };

  const itemCountLabel = (count: number) =>
    t("expenseGroupItemCount").replace("{count}", String(count));

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

      {!loading && rows.length > 0 ? (
        <ExpenseListControls
          groupByCategory={groupByCategory}
          sortField={sortField}
          sortDir={sortDir}
          labels={{
            groupByCategory: t("expenseGroupByCategory"),
            sortBy: t("expenseSortBy"),
            sortDate: t("expenseSortDate"),
            sortAmount: t("expenseSortAmount"),
            dateLateToEarly: t("expenseSortDateLateToEarly"),
            dateEarlyToLate: t("expenseSortDateEarlyToLate"),
            amountLargeToSmall: t("expenseSortAmountLargeToSmall"),
            amountSmallToLarge: t("expenseSortAmountSmallToLarge"),
          }}
          onGroupByCategoryChange={handleGroupByCategoryChange}
          onSortFieldChange={setSortField}
          onSortDirChange={setSortDir}
        />
      ) : null}

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
      ) : groupByCategory ? (
        loadingAll ? (
          <p className="text-center text-sm text-gray-500 py-8">{t("loading")}</p>
        ) : (
          <ExpenseGroupList
            groups={l1Groups}
            itemCountLabel={itemCountLabel}
            {...rowProps}
          />
        )
      ) : (
        <div className="space-y-3">
          <ul className="divide-y divide-gray-100 rounded-xl border border-gray-100 bg-white shadow-sm">
            {sortedRows.map((row) => (
              <ExpenseRowItem key={row.id} row={row} {...rowProps} />
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
          onSaved={handleExpenseSaved}
        />
      ) : null}
    </div>
  );
}
