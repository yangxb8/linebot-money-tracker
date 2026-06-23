"use client";

import { useLanguage } from "@/components/LanguageProvider";
import {
  computeBudgetHealth,
  healthToneClass,
  progressBarClass,
} from "@/lib/budget/health";
import { formatPercent, formatYen } from "@/lib/budget/format";
import type { BudgetCategoryNode } from "@/lib/budget/types";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  node: BudgetCategoryNode;
  elapsedDays: number;
  daysInMonth: number;
  onEdit?: () => void;
};

export function BudgetRow({
  node,
  elapsedDays,
  daysInMonth,
  onEdit,
}: Props) {
  const { t, locale } = useLanguage();
  const limit = node.limit;
  const spent = node.has_limit ? node.spent_assigned : node.spent_aggregate;
  const health = computeBudgetHealth(spent, limit, elapsedDays, daysInMonth);
  const fmt = (n: number) => formatYen(n, locale as Locale);
  const spentPct = limit != null && limit > 0 ? spent / limit : null;
  const progressPct = spentPct != null ? Math.min(100, spentPct * 100) : 0;
  const overAmount =
    limit != null && spent > limit ? spent - limit : 0;

  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium text-gray-900">{node.name_ja}</p>
        {onEdit ? (
          <button
            type="button"
            onClick={onEdit}
            className="text-xs text-gray-500 underline"
          >
            {t("edit")}
          </button>
        ) : null}
      </div>

      {!node.has_limit ? (
        <p className="mt-1 text-sm text-gray-600">
          {t("budgetSpentLabel")}: {fmt(node.spent_aggregate)}
          <span className="text-gray-400"> · {t("budgetNoLimit")}</span>
        </p>
      ) : (
        <>
          <p className="mt-1 text-sm text-gray-800">
            {fmt(spent)} / {limit != null ? fmt(limit) : "—"}
          </p>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-200">
            <div
              className={`h-full ${progressBarClass(health.tone)}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className="mt-1 flex flex-wrap gap-2 text-xs">
            <span className={`rounded px-1.5 py-0.5 ${healthToneClass(health.tone)}`}>
              {t(health.labelKey)}
            </span>
            {spentPct != null ? (
              <span className="text-gray-500">{formatPercent(spentPct)}</span>
            ) : null}
          </div>
          {overAmount > 0 ? (
            <p className="mt-1 text-xs font-medium text-red-600">
              +{fmt(overAmount)} {t("budgetOverShort")}
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}
