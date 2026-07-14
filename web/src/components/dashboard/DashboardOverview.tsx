"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { DashboardBudgetCard } from "@/components/dashboard/DashboardBudgetCard";
import { SpendDistributionRing } from "@/components/dashboard/SpendDistributionRing";
import { fetchBudgetSummary } from "@/lib/budget/client";
import {
  buildL1SpendSlices,
  selectAttentionL1Categories,
} from "@/lib/dashboard/overview";
import type { BudgetSummary } from "@/lib/budget/types";
import type { TenantOption } from "@/lib/dashboard/tenants";

type Props = {
  tenant: TenantOption;
  budgetMonth: string;
};

export function DashboardOverview({ tenant, budgetMonth }: Props) {
  const { t } = useLanguage();
  const router = useRouter();
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    void fetchBudgetSummary(tenant, budgetMonth)
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        if (!cancelled) {
          setSummary(null);
          setError(true);
        }
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

  const goToBudget = () => {
    router.push("/budget");
  };

  if (error || !summary) {
    return null;
  }

  const showBudgetCards = summary.has_any_limit;
  const showRing = spendSlices.length > 0;

  if (!showBudgetCards && !showRing) {
    return null;
  }

  return (
    <div className="space-y-3">
      {showBudgetCards ? (
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
            elapsedDays={summary.elapsed_days}
            daysInMonth={summary.days_in_month}
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
        </div>
      ) : null}

      {showRing ? (
        <SpendDistributionRing
          slices={spendSlices}
          totalSpent={summary.total.spent}
        />
      ) : null}
    </div>
  );
}
