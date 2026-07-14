"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { formatYen } from "@/lib/budget/format";
import type { UpcomingPeriodicItem } from "@/lib/dashboard/overview";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  items: UpcomingPeriodicItem[];
  onOpen: () => void;
};

function formatShortDate(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${Number(month)}/${Number(day)}`;
}

export function DashboardUpcomingPeriodics({ items, onOpen }: Props) {
  const { t, locale } = useLanguage();
  const fmt = (n: number) => formatYen(n, locale as Locale);

  if (items.length === 0) return null;

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-gray-500">
          {t("dashboardUpcomingPeriodics")}
        </h2>
        <button
          type="button"
          onClick={onOpen}
          className="text-xs text-gray-500 underline"
        >
          {t("dashboardViewPeriodics")}
        </button>
      </div>
      <ul className="mt-3 divide-y divide-gray-100">
        {items.map((item) => {
          const dateLabel =
            item.dates.length === 1
              ? formatShortDate(item.dates[0]!)
              : `${formatShortDate(item.dates[0]!)} · ${item.dates.length}${t("dashboardRunCount")}`;
          return (
            <li key={item.id} className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-gray-900">
                  {item.name}
                </p>
                <p className="text-xs text-gray-500">{dateLabel}</p>
              </div>
              <p className="shrink-0 text-sm tabular-nums text-gray-800">
                {fmt(item.amount)}
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
