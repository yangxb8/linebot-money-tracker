"use client";

import type { RecurrenceKind, RecurrenceRule } from "@/lib/periodic/types";
import { useLanguage } from "@/components/LanguageProvider";

type Props = {
  value: RecurrenceRule;
  onChange: (value: RecurrenceRule) => void;
};

const KINDS: RecurrenceKind[] = [
  "interval_days",
  "monthly_days",
  "monthly_boundary",
  "every_n_months",
  "every_n_weeks",
];

export function RecurrenceFields({ value, onChange }: Props) {
  const { t } = useLanguage();

  function setKind(kind: RecurrenceKind) {
    switch (kind) {
      case "interval_days":
        onChange({ kind, interval: 20 });
        break;
      case "monthly_days":
        onChange({ kind, days: [1] });
        break;
      case "monthly_boundary":
        onChange({ kind, boundary: "first" });
        break;
      case "every_n_months":
        onChange({ kind, interval: 3, day: 15 });
        break;
      case "every_n_weeks":
        onChange({ kind, interval: 1, weekdays: [1] });
        break;
    }
  }

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        {t("periodicRecurrence")}
      </label>
      <select
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        value={value.kind}
        onChange={(e) => setKind(e.target.value as RecurrenceKind)}
      >
        {KINDS.map((kind) => (
          <option key={kind} value={kind}>
            {t(`recurrenceKind_${kind}` as never)}
          </option>
        ))}
      </select>

      {value.kind === "interval_days" ? (
        <div>
          <label className="text-xs text-gray-500">{t("periodicIntervalDays")}</label>
          <input
            type="number"
            min={1}
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            value={value.interval}
            onChange={(e) =>
              onChange({ ...value, interval: Number(e.target.value) || 1 })
            }
          />
        </div>
      ) : null}

      {value.kind === "monthly_days" ? (
        <div>
          <label className="text-xs text-gray-500">{t("periodicMonthlyDays")}</label>
          <input
            type="text"
            placeholder="1, 15"
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            value={value.days.join(", ")}
            onChange={(e) => {
              const days = e.target.value
                .split(/[,，\s]+/)
                .map((s) => Number(s.trim()))
                .filter((n) => Number.isInteger(n) && n >= 1 && n <= 31);
              onChange({ ...value, days: days.length ? days : [1] });
            }}
          />
        </div>
      ) : null}

      {value.kind === "monthly_boundary" ? (
        <select
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          value={value.boundary}
          onChange={(e) =>
            onChange({
              ...value,
              boundary: e.target.value as "first" | "last",
            })
          }
        >
          <option value="first">{t("recurrenceBoundaryFirst")}</option>
          <option value="last">{t("recurrenceBoundaryLast")}</option>
        </select>
      ) : null}

      {value.kind === "every_n_months" ? (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-500">{t("periodicEveryNMonths")}</label>
            <input
              type="number"
              min={1}
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              value={value.interval}
              onChange={(e) =>
                onChange({ ...value, interval: Number(e.target.value) || 1 })
              }
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">{t("periodicDayOfMonth")}</label>
            <input
              type="number"
              min={1}
              max={31}
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              value={value.day}
              onChange={(e) =>
                onChange({ ...value, day: Number(e.target.value) || 1 })
              }
            />
          </div>
        </div>
      ) : null}

      {value.kind === "every_n_weeks" ? (
        <div className="space-y-2">
          <div>
            <label className="text-xs text-gray-500">{t("periodicEveryNWeeks")}</label>
            <input
              type="number"
              min={1}
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              value={value.interval}
              onChange={(e) =>
                onChange({ ...value, interval: Number(e.target.value) || 1 })
              }
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {[0, 1, 2, 3, 4, 5, 6].map((wd) => {
              const selected = value.weekdays.includes(wd);
              return (
                <button
                  key={wd}
                  type="button"
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    selected
                      ? "bg-gray-900 text-white"
                      : "border border-gray-200 text-gray-600"
                  }`}
                  onClick={() => {
                    const weekdays = selected
                      ? value.weekdays.filter((w) => w !== wd)
                      : [...value.weekdays, wd].sort((a, b) => a - b);
                    onChange({
                      ...value,
                      weekdays: weekdays.length ? weekdays : [wd],
                    });
                  }}
                >
                  {t(`weekdayShort_${wd}` as never)}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
