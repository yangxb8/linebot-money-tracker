"use client";

import { useLanguage } from "@/components/LanguageProvider";
import {
  computeBudgetHealth,
  healthToneClass,
  progressBarClass,
} from "@/lib/budget/health";
import { formatPercent, formatYen } from "@/lib/budget/format";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  title: string;
  spent: number;
  limit: number | null;
  hasLimit: boolean;
  elapsedDays: number;
  daysInMonth: number;
  onClick: () => void;
};

export function DashboardBudgetCard({
  title,
  spent,
  limit,
  hasLimit,
  elapsedDays,
  daysInMonth,
  onClick,
}: Props) {
  const { t, locale } = useLanguage();
  const health = computeBudgetHealth(spent, limit, elapsedDays, daysInMonth);
  const fmt = (n: number) => formatYen(n, locale as Locale);
  const progressPct =
    hasLimit && limit != null && limit > 0
      ? Math.min(100, (spent / limit) * 100)
      : 0;

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-xl border border-gray-200 bg-white p-3 text-left shadow-sm transition hover:border-gray-300 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        {hasLimit ? (
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${healthToneClass(health.tone)}`}
          >
            {t(health.labelKey)}
          </span>
        ) : null}
      </div>
      <p className="mt-1 text-lg font-semibold text-gray-900">
        {fmt(spent)}
        {hasLimit && limit != null ? (
          <span className="text-sm font-normal text-gray-500">
            {" "}
            / {fmt(limit)}
          </span>
        ) : null}
      </p>
      {hasLimit ? (
        <>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-100">
            <div
              className={`h-full ${progressBarClass(health.tone)}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
          {health.spentPct != null ? (
            <p className="mt-1 text-xs text-gray-500">
              {formatPercent(health.spentPct)} {t("budgetSpentLabel")}
            </p>
          ) : null}
        </>
      ) : (
        <p className="mt-1 text-xs text-gray-500">{t("budgetNoLimit")}</p>
      )}
    </button>
  );
}
