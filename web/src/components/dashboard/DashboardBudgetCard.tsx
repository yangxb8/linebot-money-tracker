"use client";

import { useLanguage } from "@/components/LanguageProvider";
import {
  computeBudgetHealth,
  healthToneClass,
  progressBarClass,
} from "@/lib/budget/health";
import { formatPercent, formatYen } from "@/lib/budget/format";
import { dailyRemainingAllowance } from "@/lib/dashboard/overview";
import type { BudgetCategoryNode, BudgetMeter } from "@/lib/budget/types";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  total: BudgetMeter;
  attentionCategories: BudgetCategoryNode[];
  unbudgetedSpent: number;
  elapsedDays: number;
  daysInMonth: number;
  onClick: () => void;
};

export function DashboardBudgetCard({
  total,
  attentionCategories,
  unbudgetedSpent,
  elapsedDays,
  daysInMonth,
  onClick,
}: Props) {
  const { t, locale } = useLanguage();
  const health = computeBudgetHealth(
    total.spent,
    total.limit,
    elapsedDays,
    daysInMonth,
  );
  const fmt = (n: number) => formatYen(n, locale as Locale);
  const progressPct =
    total.has_limit && total.limit != null && total.limit > 0
      ? Math.min(100, (total.spent / total.limit) * 100)
      : 0;
  const daysLeft = Math.max(0, daysInMonth - elapsedDays);
  const daily = total.has_limit
    ? dailyRemainingAllowance(total.remaining, daysLeft)
    : null;

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-gray-300 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-500">
          {t("budgetTotalTitle")}
        </p>
        {total.has_limit ? (
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${healthToneClass(health.tone)}`}
          >
            {t(health.labelKey)}
          </span>
        ) : null}
      </div>

      <p className="mt-1 text-xl font-semibold text-gray-900">
        {fmt(total.spent)}
        {total.has_limit && total.limit != null ? (
          <span className="text-sm font-normal text-gray-500">
            {" "}
            / {fmt(total.limit)}
          </span>
        ) : null}
      </p>

      {total.has_limit ? (
        <>
          <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-gray-100">
            <div
              className={`h-full ${progressBarClass(health.tone)}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-gray-500">
            {health.spentPct != null ? (
              <span>
                {formatPercent(health.spentPct)} {t("budgetSpentLabel")}
              </span>
            ) : null}
            {total.remaining != null ? (
              <span>
                {fmt(total.remaining)} {t("budgetRemainingShort")}
              </span>
            ) : null}
            {daily != null ? (
              <span className="font-medium text-gray-700">
                {fmt(daily)}
                {t("budgetPerDay")}
              </span>
            ) : null}
            {daysLeft > 0 ? (
              <span>
                {daysLeft}
                {t("budgetDaysLeft")}
              </span>
            ) : null}
          </div>
        </>
      ) : (
        <p className="mt-1 text-xs text-gray-500">{t("budgetNoLimit")}</p>
      )}

      {attentionCategories.length > 0 ? (
        <ul className="mt-3 space-y-2 border-t border-gray-100 pt-3">
          {attentionCategories.map((node) => {
            const rowHealth = computeBudgetHealth(
              node.spent_aggregate,
              node.limit,
              elapsedDays,
              daysInMonth,
            );
            const rowPct =
              node.limit != null && node.limit > 0
                ? Math.min(100, (node.spent_aggregate / node.limit) * 100)
                : 0;
            return (
              <li key={node.node_id} className="space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-gray-800">
                    {node.name_ja}
                  </span>
                  <span
                    className={`shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium ${healthToneClass(rowHealth.tone)}`}
                  >
                    {t(rowHealth.labelKey)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2 text-xs text-gray-600">
                  <span>
                    {fmt(node.spent_aggregate)}
                    {node.limit != null ? ` / ${fmt(node.limit)}` : ""}
                  </span>
                  {rowHealth.spentPct != null ? (
                    <span>{formatPercent(rowHealth.spentPct)}</span>
                  ) : null}
                </div>
                <div className="h-1 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className={`h-full ${progressBarClass(rowHealth.tone)}`}
                    style={{ width: `${rowPct}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}

      {unbudgetedSpent > 0 ? (
        <p className="mt-3 border-t border-gray-100 pt-2 text-xs text-amber-800">
          {t("budgetUnbudgetedCallout")}: {fmt(unbudgetedSpent)}
        </p>
      ) : null}
    </button>
  );
}
