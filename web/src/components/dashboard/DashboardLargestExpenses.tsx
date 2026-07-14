"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { formatYen } from "@/lib/budget/format";
import type { LargestExpenseItem } from "@/lib/dashboard/overview";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  items: LargestExpenseItem[];
};

function formatShortDate(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${Number(month)}/${Number(day)}`;
}

export function DashboardLargestExpenses({ items }: Props) {
  const { t, locale } = useLanguage();
  const fmt = (n: number) => formatYen(n, locale as Locale);

  if (items.length === 0) return null;

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-medium text-gray-500">
        {t("dashboardLargestExpenses")}
      </h2>
      <ul className="mt-3 divide-y divide-gray-100">
        {items.map((item) => {
          const subtitle = [formatShortDate(item.expense_date), item.category_label]
            .filter(Boolean)
            .join(" · ");
          const title = item.merchant_display?.trim() || item.description;
          return (
            <li
              key={item.id}
              className="flex items-start justify-between gap-3 py-2 first:pt-0 last:pb-0"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-gray-900">
                  {title}
                </p>
                <p className="truncate text-xs text-gray-500">{subtitle}</p>
              </div>
              <p className="shrink-0 text-sm tabular-nums text-gray-900">
                {fmt(item.amount)}
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
