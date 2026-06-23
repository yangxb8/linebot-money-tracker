"use client";

import { useLanguage } from "@/components/LanguageProvider";
import {
  computeBudgetHealth,
  healthToneClass,
  progressBarClass,
} from "@/lib/budget/health";
import { formatPercent, formatYen } from "@/lib/budget/format";
import type { BudgetMeter } from "@/lib/budget/types";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  total: BudgetMeter;
  elapsedDays: number;
  daysInMonth: number;
  hasAnyLimit: boolean;
  onEdit?: () => void;
};

export function BudgetTotalCard({
  total,
  elapsedDays,
  daysInMonth,
  hasAnyLimit,
  onEdit,
}: Props) {
  const { t, locale } = useLanguage();
  const health = computeBudgetHealth(
    total.spent,
    total.limit,
    elapsedDays,
    daysInMonth,
  );
  const fmt = (n: number) => formatYen(n, locale as Locale);
  const progressPct = total.has_limit
    ? Math.min(100, (total.spent_pct ?? 0) * 100)
    : 0;
  const overAmount =
    total.has_limit && total.limit != null && total.spent > total.limit
      ? total.spent - total.limit
      : 0;
  const daysLeft = Math.max(0, daysInMonth - elapsedDays);
  const daily =
    total.remaining != null && daysLeft > 0
      ? Math.floor(total.remaining / daysLeft)
      : 0;

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-medium text-gray-500">{t("budgetTotalTitle")}</h2>
          {!hasAnyLimit ? (
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {t("budgetUnlimited")}
            </p>
          ) : (
            <p className="mt-1 text-2xl font-semibold text-gray-900">
              {fmt(total.spent)}
              {total.has_limit && total.limit != null ? (
                <span className="text-base font-normal text-gray-500">
                  {" "}
                  / {fmt(total.limit)}
                </span>
              ) : null}
            </p>
          )}
        </div>
        {onEdit ? (
          <button
            type="button"
            onClick={onEdit}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-700"
          >
            {t("edit")}
          </button>
        ) : null}
      </div>

      {hasAnyLimit && total.has_limit ? (
        <>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-100">
            <div
              className={`h-full transition-all ${progressBarClass(health.tone)}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${healthToneClass(health.tone)}`}
            >
              {t(health.labelKey)}
            </span>
            {total.spent_pct != null ? (
              <span className="text-gray-600">
                {formatPercent(total.spent_pct)} {t("budgetSpentLabel")}
              </span>
            ) : null}
          </div>
          {total.remaining != null ? (
            <p className="mt-2 text-sm text-gray-600">
              {fmt(total.remaining)} {t("budgetRemainingShort")} · {fmt(daily)}
              {t("budgetPerDay")} · {daysLeft}
              {t("budgetDaysLeft")}
            </p>
          ) : null}
          {overAmount > 0 ? (
            <p className="mt-1 text-sm font-medium text-red-600">
              {fmt(overAmount)} {t("budgetOverShort")}
            </p>
          ) : null}
        </>
      ) : (
        <p className="mt-2 text-sm text-gray-600">
          {t("budgetSpentLabel")}: {fmt(total.spent)}
        </p>
      )}
    </section>
  );
}
