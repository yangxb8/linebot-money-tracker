"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { formatPercent, formatYen } from "@/lib/budget/format";
import type { MerchantSpend } from "@/lib/dashboard/overview";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  merchants: MerchantSpend[];
};

export function DashboardTopMerchants({ merchants }: Props) {
  const { t, locale } = useLanguage();
  const fmt = (n: number) => formatYen(n, locale as Locale);

  if (merchants.length === 0) return null;

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-medium text-gray-500">
        {t("dashboardTopMerchants")}
      </h2>
      <ul className="mt-3 space-y-2">
        {merchants.map((merchant) => (
          <li key={merchant.label} className="flex items-center gap-2 text-sm">
            <span className="min-w-0 flex-1 truncate text-gray-800">
              {merchant.label}
            </span>
            <span className="shrink-0 text-xs text-gray-400">
              {formatPercent(merchant.pct)}
            </span>
            <span className="shrink-0 tabular-nums text-gray-900">
              {fmt(merchant.amount)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
