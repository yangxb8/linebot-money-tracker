"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { DashboardBudgetCard } from "@/components/dashboard/DashboardBudgetCard";
import { DashboardLargestExpenses } from "@/components/dashboard/DashboardLargestExpenses";
import { DashboardTopMerchants } from "@/components/dashboard/DashboardTopMerchants";
import { DashboardUpcomingPeriodics } from "@/components/dashboard/DashboardUpcomingPeriodics";
import { SpendDistributionRing } from "@/components/dashboard/SpendDistributionRing";
import { fetchBudgetSummary } from "@/lib/budget/client";
import {
  fiscalPeriodEnd,
  formatYen,
  getTodayJst,
  isCurrentBudgetMonth,
} from "@/lib/budget/format";
import {
  buildL1SpendSlices,
  buildTopMerchants,
  selectAttentionL1Categories,
  selectLargestNonPeriodicExpenses,
  selectUpcomingPeriodics,
  shouldShowUnbudgeted,
} from "@/lib/dashboard/overview";
import type { BudgetSummary } from "@/lib/budget/types";
import { PAGE_SIZE } from "@/lib/dashboard/format";
import type { TenantOption } from "@/lib/dashboard/tenants";
import { fetchAllExpensesForMonth } from "@/lib/expenses/client";
import type { ExpenseRecord } from "@/lib/expenses/types";
import { fetchPeriodicSchedules } from "@/lib/periodic/client";
import type { PeriodicScheduleResponse } from "@/lib/periodic/types";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  tenant: TenantOption;
  budgetMonth: string;
};

function todayIsoJst(): string {
  const today = getTodayJst();
  return `${today.year}-${String(today.month).padStart(2, "0")}-${String(today.day).padStart(2, "0")}`;
}

export function DashboardOverview({ tenant, budgetMonth }: Props) {
  const { t, locale } = useLanguage();
  const router = useRouter();
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [schedules, setSchedules] = useState<PeriodicScheduleResponse[]>([]);
  const [expenses, setExpenses] = useState<ExpenseRecord[]>([]);
  const [budgetError, setBudgetError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setBudgetError(false);
    void fetchBudgetSummary(tenant, budgetMonth)
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        if (!cancelled) {
          setSummary(null);
          setBudgetError(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [tenant, budgetMonth]);

  useEffect(() => {
    let cancelled = false;
    void fetchPeriodicSchedules(tenant)
      .then((data) => {
        if (!cancelled) setSchedules(data);
      })
      .catch(() => {
        if (!cancelled) setSchedules([]);
      });
    return () => {
      cancelled = true;
    };
  }, [tenant]);

  useEffect(() => {
    let cancelled = false;
    void fetchAllExpensesForMonth(tenant, budgetMonth, PAGE_SIZE)
      .then((rows) => {
        if (!cancelled) setExpenses(rows);
      })
      .catch(() => {
        if (!cancelled) setExpenses([]);
      });
    return () => {
      cancelled = true;
    };
  }, [tenant, budgetMonth]);

  const attentionL1 = useMemo(() => {
    if (!summary?.has_any_limit) return [];
    return selectAttentionL1Categories(
      summary.categories,
      summary.elapsed_days,
      summary.days_in_month,
    );
  }, [summary]);

  const spendSlices = useMemo(() => {
    if (!summary) return [];
    return buildL1SpendSlices(summary.categories, {
      otherLabel: t("dashboardOtherCategory"),
    });
  }, [summary, t]);

  const upcoming = useMemo(() => {
    if (!summary) return [];
    const fiscalStartDay = summary.fiscal_start_day ?? 1;
    if (!isCurrentBudgetMonth(budgetMonth, fiscalStartDay)) return [];
    const periodEnd = summary.fiscal_period_end ?? fiscalPeriodEnd(budgetMonth);
    return selectUpcomingPeriodics(schedules, {
      periodEnd,
      fromDate: todayIsoJst(),
    });
  }, [summary, schedules, budgetMonth]);

  const topMerchants = useMemo(
    () => buildTopMerchants(expenses, { limit: 5 }),
    [expenses],
  );

  const largestExpenses = useMemo(
    () => selectLargestNonPeriodicExpenses(expenses, { limit: 5 }),
    [expenses],
  );

  const goToBudget = () => {
    router.push("/budget");
  };

  const goToPeriodics = () => {
    router.push("/periodic-expenses");
  };

  if (budgetError && expenses.length === 0 && schedules.length === 0) {
    return null;
  }

  const showBudgetCards = Boolean(summary?.has_any_limit);
  const showUnbudgeted =
    summary != null &&
    shouldShowUnbudgeted(summary.unbudgeted_spent, summary.has_any_limit);
  const showRing = spendSlices.length > 0;
  const showUpcoming = upcoming.length > 0;
  const showMerchants = topMerchants.length > 0;
  const showLargest = largestExpenses.length > 0;

  if (
    !showBudgetCards &&
    !showUnbudgeted &&
    !showRing &&
    !showUpcoming &&
    !showMerchants &&
    !showLargest
  ) {
    return null;
  }

  const fmt = (n: number) => formatYen(n, locale as Locale);

  return (
    <div className="space-y-3">
      {showBudgetCards && summary ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-medium text-gray-500">
              {t("dashboardBudgetSection")}
            </h2>
            <button
              type="button"
              onClick={goToBudget}
              className="text-xs text-gray-500 underline"
            >
              {t("dashboardViewBudget")}
            </button>
          </div>
          <DashboardBudgetCard
            title={t("budgetTotalTitle")}
            spent={summary.total.spent}
            limit={summary.total.limit}
            hasLimit={summary.total.has_limit}
            remaining={summary.total.remaining}
            elapsedDays={summary.elapsed_days}
            daysInMonth={summary.days_in_month}
            showDailyRemaining={summary.total.has_limit}
            onClick={goToBudget}
          />
          {attentionL1.length > 0 ? (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {attentionL1.map((node) => (
                <DashboardBudgetCard
                  key={node.node_id}
                  title={node.name_ja}
                  spent={node.spent_aggregate}
                  limit={node.limit}
                  hasLimit={node.has_limit}
                  elapsedDays={summary.elapsed_days}
                  daysInMonth={summary.days_in_month}
                  onClick={goToBudget}
                />
              ))}
            </div>
          ) : null}
          {showUnbudgeted ? (
            <button
              type="button"
              onClick={goToBudget}
              className="w-full rounded-lg bg-amber-50 px-3 py-2 text-left text-sm text-amber-800 transition hover:bg-amber-100"
            >
              {t("budgetUnbudgetedCallout")}: {fmt(summary.unbudgeted_spent)}
            </button>
          ) : null}
        </div>
      ) : null}

      {showRing && summary ? (
        <SpendDistributionRing
          slices={spendSlices}
          totalSpent={summary.total.spent}
        />
      ) : null}

      {showUpcoming ? (
        <DashboardUpcomingPeriodics
          items={upcoming}
          onOpen={goToPeriodics}
        />
      ) : null}

      {showMerchants ? (
        <DashboardTopMerchants merchants={topMerchants} />
      ) : null}

      {showLargest ? (
        <DashboardLargestExpenses items={largestExpenses} />
      ) : null}
    </div>
  );
}
