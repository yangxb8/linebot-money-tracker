"use client";

import type {
  RecurrenceFieldKey,
  RecurrenceFormErrors,
  RecurrenceFormRule,
} from "@/lib/periodic/form";
import type { RecurrenceKind } from "@/lib/periodic/types";
import { useLanguage } from "@/components/LanguageProvider";

type Props = {
  value: RecurrenceFormRule;
  onChange: (value: RecurrenceFormRule) => void;
  fieldErrors?: RecurrenceFormErrors;
};

const KINDS: RecurrenceKind[] = [
  "interval_days",
  "monthly_days",
  "monthly_boundary",
  "every_n_months",
  "every_n_weeks",
];

function fieldClass(invalid?: boolean) {
  return `mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
    invalid
      ? "border-red-500 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-200"
      : "border-gray-200"
  }`;
}

export function RecurrenceFields({ value, onChange, fieldErrors }: Props) {
  const { t } = useLanguage();

  function setKind(kind: RecurrenceKind) {
    switch (kind) {
      case "interval_days":
        onChange({ kind, interval: "20" });
        break;
      case "monthly_days":
        onChange({ kind, daysText: "1" });
        break;
      case "monthly_boundary":
        onChange({ kind, boundary: "first" });
        break;
      case "every_n_months":
        onChange({ kind, interval: "3", day: "15" });
        break;
      case "every_n_weeks":
        onChange({ kind, interval: "1", weekdays: [1] });
        break;
    }
  }

  function invalid(key: RecurrenceFieldKey) {
    return Boolean(fieldErrors?.[key]);
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
            type="text"
            inputMode="numeric"
            className={fieldClass(invalid("interval"))}
            value={value.interval}
            onChange={(e) => onChange({ ...value, interval: e.target.value })}
          />
        </div>
      ) : null}

      {value.kind === "monthly_days" ? (
        <div>
          <label className="text-xs text-gray-500">{t("periodicMonthlyDays")}</label>
          <input
            type="text"
            placeholder="1, 15"
            className={fieldClass(invalid("daysText"))}
            value={value.daysText}
            onChange={(e) => onChange({ ...value, daysText: e.target.value })}
          />
          <p className="mt-1 text-xs text-gray-400">{t("periodicDayOfMonthHint")}</p>
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
              type="text"
              inputMode="numeric"
              className={fieldClass(invalid("interval"))}
              value={value.interval}
              onChange={(e) => onChange({ ...value, interval: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">{t("periodicDayOfMonth")}</label>
            <input
              type="text"
              inputMode="numeric"
              className={fieldClass(invalid("day"))}
              value={value.day}
              onChange={(e) => onChange({ ...value, day: e.target.value })}
            />
            <p className="mt-1 text-xs text-gray-400">{t("periodicDayOfMonthHint")}</p>
          </div>
        </div>
      ) : null}

      {value.kind === "every_n_weeks" ? (
        <div className="space-y-2">
          <div>
            <label className="text-xs text-gray-500">{t("periodicEveryNWeeks")}</label>
            <input
              type="text"
              inputMode="numeric"
              className={fieldClass(invalid("interval"))}
              value={value.interval}
              onChange={(e) => onChange({ ...value, interval: e.target.value })}
            />
          </div>
          <div>
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
                      onChange({ ...value, weekdays });
                    }}
                  >
                    {t(`weekdayShort_${wd}` as never)}
                  </button>
                );
              })}
            </div>
            {invalid("weekdays") ? (
              <p className="mt-1 text-xs text-red-600">{t("periodicErrorRecurrenceWeekdays")}</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
