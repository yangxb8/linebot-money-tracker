import type { RecurrenceRule } from "@/lib/periodic/types";

/** Recurrence rule as editable form strings (allows empty while typing). */
export type RecurrenceFormRule =
  | { kind: "interval_days"; interval: string }
  | { kind: "monthly_days"; daysText: string }
  | { kind: "monthly_boundary"; boundary: "first" | "last" }
  | { kind: "every_n_months"; interval: string; day: string }
  | { kind: "every_n_weeks"; interval: string; weekdays: number[] };

export type RecurrenceFieldKey = "interval" | "daysText" | "day" | "weekdays";

export type RecurrenceFormErrors = Partial<Record<RecurrenceFieldKey, boolean>>;

function parsePositiveInt(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  if (!Number.isInteger(n) || n < 1) return null;
  return n;
}

function parseDayOfMonth(raw: string): number | null {
  const n = parsePositiveInt(raw);
  if (n == null || n > 31) return null;
  return n;
}

export function recurrenceToForm(rule: RecurrenceRule): RecurrenceFormRule {
  switch (rule.kind) {
    case "interval_days":
      return { kind: rule.kind, interval: String(rule.interval) };
    case "monthly_days":
      return { kind: rule.kind, daysText: rule.days.join(", ") };
    case "monthly_boundary":
      return { kind: rule.kind, boundary: rule.boundary };
    case "every_n_months":
      return {
        kind: rule.kind,
        interval: String(rule.interval),
        day: String(rule.day),
      };
    case "every_n_weeks":
      return {
        kind: rule.kind,
        interval: String(rule.interval),
        weekdays: [...rule.weekdays],
      };
  }
}

export function defaultRecurrenceForm(): RecurrenceFormRule {
  return { kind: "monthly_days", daysText: "1" };
}

export function parseRecurrenceForm(
  form: RecurrenceFormRule,
):
  | { ok: true; rule: RecurrenceRule }
  | { ok: false; errorKey: string; fields: RecurrenceFormErrors } {
  switch (form.kind) {
    case "interval_days": {
      const interval = parsePositiveInt(form.interval);
      if (interval == null) {
        return {
          ok: false,
          errorKey: "periodicErrorRecurrenceInterval",
          fields: { interval: true },
        };
      }
      return { ok: true, rule: { kind: form.kind, interval } };
    }
    case "monthly_days": {
      const parts = form.daysText
        .split(/[,，\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      if (parts.length === 0) {
        return {
          ok: false,
          errorKey: "periodicErrorRecurrenceDays",
          fields: { daysText: true },
        };
      }
      const days: number[] = [];
      for (const part of parts) {
        const day = parseDayOfMonth(part);
        if (day == null) {
          return {
            ok: false,
            errorKey: "periodicErrorRecurrenceDays",
            fields: { daysText: true },
          };
        }
        if (!days.includes(day)) days.push(day);
      }
      days.sort((a, b) => a - b);
      return { ok: true, rule: { kind: form.kind, days } };
    }
    case "monthly_boundary":
      return { ok: true, rule: { kind: form.kind, boundary: form.boundary } };
    case "every_n_months": {
      const interval = parsePositiveInt(form.interval);
      const day = parseDayOfMonth(form.day);
      const fields: RecurrenceFormErrors = {};
      if (interval == null) fields.interval = true;
      if (day == null) fields.day = true;
      if (interval == null || day == null) {
        return {
          ok: false,
          errorKey: interval == null
            ? "periodicErrorRecurrenceInterval"
            : "periodicErrorRecurrenceDay",
          fields,
        };
      }
      return { ok: true, rule: { kind: form.kind, interval, day } };
    }
    case "every_n_weeks": {
      const interval = parsePositiveInt(form.interval);
      const fields: RecurrenceFormErrors = {};
      if (interval == null) fields.interval = true;
      if (form.weekdays.length === 0) fields.weekdays = true;
      if (interval == null || form.weekdays.length === 0) {
        return {
          ok: false,
          errorKey:
            interval == null
              ? "periodicErrorRecurrenceInterval"
              : "periodicErrorRecurrenceWeekdays",
          fields,
        };
      }
      return {
        ok: true,
        rule: {
          kind: form.kind,
          interval,
          weekdays: [...form.weekdays].sort((a, b) => a - b),
        },
      };
    }
  }
}
