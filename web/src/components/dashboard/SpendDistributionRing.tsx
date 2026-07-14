"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { formatPercent, formatYen } from "@/lib/budget/format";
import {
  SPEND_RING_COLORS,
  type SpendSlice,
} from "@/lib/dashboard/overview";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  slices: SpendSlice[];
  totalSpent: number;
};

const SIZE = 140;
const STROKE = 18;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function SpendDistributionRing({ slices, totalSpent }: Props) {
  const { t, locale } = useLanguage();
  const fmt = (n: number) => formatYen(n, locale as Locale);

  if (slices.length === 0) return null;

  let offset = 0;
  const arcs = slices.map((slice, index) => {
    const length = slice.pct * CIRCUMFERENCE;
    const dashoffset = -offset;
    offset += length;
    return {
      ...slice,
      length,
      dashoffset,
      color: SPEND_RING_COLORS[index % SPEND_RING_COLORS.length],
    };
  });

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-medium text-gray-500">
        {t("dashboardSpendByCategory")}
      </h2>
      <div className="mt-3 flex items-center gap-4">
        <div className="relative shrink-0" style={{ width: SIZE, height: SIZE }}>
          <svg
            width={SIZE}
            height={SIZE}
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            role="img"
            aria-label={t("dashboardSpendByCategory")}
          >
            <circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADIUS}
              fill="none"
              stroke="#f3f4f6"
              strokeWidth={STROKE}
            />
            {arcs.map((arc) => (
              <circle
                key={arc.id}
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={RADIUS}
                fill="none"
                stroke={arc.color}
                strokeWidth={STROKE}
                strokeDasharray={`${arc.length} ${CIRCUMFERENCE - arc.length}`}
                strokeDashoffset={arc.dashoffset}
                strokeLinecap="butt"
                transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
              />
            ))}
          </svg>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
            <p className="text-xs text-gray-500">{t("dashboardRingTotal")}</p>
            <p className="text-sm font-semibold text-gray-900">{fmt(totalSpent)}</p>
          </div>
        </div>
        <ul className="min-w-0 flex-1 space-y-1.5">
          {arcs.map((arc) => (
            <li key={arc.id} className="flex items-center gap-2 text-xs">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: arc.color }}
                aria-hidden
              />
              <span className="min-w-0 flex-1 truncate text-gray-700">
                {arc.label}
              </span>
              <span className="shrink-0 tabular-nums text-gray-500">
                {formatPercent(arc.pct)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
