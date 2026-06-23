import type { RecurrenceRule } from "@/lib/periodic/types";

/** ISO date string YYYY-MM-DD in the given IANA timezone. */
export function localTodayIso(timezone: string, now = new Date()): string {
  return formatDateInTimezone(now, timezone);
}

function formatDateInTimezone(date: Date, timezone: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function parseIsoDate(iso: string): { y: number; m: number; d: number } {
  const [y, m, d] = iso.split("-").map(Number);
  return { y, m, d };
}

function toIso(y: number, m: number, d: number): string {
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

function daysInMonth(y: number, m: number): number {
  return new Date(Date.UTC(y, m, 0)).getUTCDate();
}

function clampDay(y: number, m: number, day: number): number {
  return Math.min(day, daysInMonth(y, m));
}

function addDays(iso: string, days: number): string {
  const { y, m, d } = parseIsoDate(iso);
  const dt = new Date(Date.UTC(y, m - 1, d + days));
  return toIso(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate());
}

function compareIso(a: string, b: string): number {
  return a.localeCompare(b);
}

function monthBoundaryDate(y: number, m: number, boundary: "first" | "last"): string {
  if (boundary === "first") return toIso(y, m, 1);
  return toIso(y, m, daysInMonth(y, m));
}

function weekdayFromIso(iso: string): number {
  const { y, m, d } = parseIsoDate(iso);
  return new Date(Date.UTC(y, m - 1, d)).getUTCDay();
}

function isoFromWeekdayOnOrAfter(
  iso: string,
  weekday: number,
  everyNWeeks: number,
  anchorIso: string,
): string | null {
  let cursor = iso;
  for (let i = 0; i < 366 * 3; i++) {
    if (weekdayFromIso(cursor) === weekday) {
      const anchor = parseIsoDate(anchorIso);
      const cur = parseIsoDate(cursor);
      const anchorMs = Date.UTC(anchor.y, anchor.m - 1, anchor.d);
      const curMs = Date.UTC(cur.y, cur.m - 1, cur.d);
      const weekDiff = Math.floor((curMs - anchorMs) / (7 * 24 * 3600 * 1000));
      if (weekDiff >= 0 && weekDiff % everyNWeeks === 0) {
        return cursor;
      }
    }
    cursor = addDays(cursor, 1);
  }
  return null;
}

function nextMonthlyDays(
  rule: Extract<RecurrenceRule, { kind: "monthly_days" }>,
  startDate: string,
  afterDate: string,
): string | null {
  const days = [...rule.days].sort((a, b) => a - b);
  const { y, m } = parseIsoDate(startDate);

  for (let monthOffset = 0; monthOffset < 240; monthOffset++) {
    let yy = y;
    let mm = m + monthOffset;
    while (mm > 12) {
      mm -= 12;
      yy += 1;
    }
    for (const day of days) {
      const d = clampDay(yy, mm, day);
      const candidate = toIso(yy, mm, d);
      if (compareIso(candidate, startDate) >= 0 && compareIso(candidate, afterDate) > 0) {
        return candidate;
      }
    }
  }
  return null;
}

function nextMonthlyBoundary(
  rule: Extract<RecurrenceRule, { kind: "monthly_boundary" }>,
  startDate: string,
  afterDate: string,
): string | null {
  const { y, m } = parseIsoDate(startDate);
  for (let monthOffset = 0; monthOffset < 240; monthOffset++) {
    let yy = y;
    let mm = m + monthOffset;
    while (mm > 12) {
      mm -= 12;
      yy += 1;
    }
    const candidate = monthBoundaryDate(yy, mm, rule.boundary);
    if (compareIso(candidate, startDate) >= 0 && compareIso(candidate, afterDate) > 0) {
      return candidate;
    }
  }
  return null;
}

function nextEveryNMonths(
  rule: Extract<RecurrenceRule, { kind: "every_n_months" }>,
  startDate: string,
  afterDate: string,
): string | null {
  const start = parseIsoDate(startDate);
  for (let k = 0; k < 120; k++) {
    const totalMonths = start.m - 1 + k * rule.interval;
    const yy = start.y + Math.floor(totalMonths / 12);
    const mm = (totalMonths % 12) + 1;
    const d = clampDay(yy, mm, rule.day);
    const candidate = toIso(yy, mm, d);
    if (compareIso(candidate, startDate) >= 0 && compareIso(candidate, afterDate) > 0) {
      return candidate;
    }
  }
  return null;
}

function nextEveryNWeeks(
  rule: Extract<RecurrenceRule, { kind: "every_n_weeks" }>,
  startDate: string,
  afterDate: string,
): string | null {
  const weekdays = [...rule.weekdays].sort((a, b) => a - b);
  let best: string | null = null;
  let cursor = compareIso(afterDate, startDate) >= 0 ? addDays(afterDate, 1) : startDate;

  for (let i = 0; i < 366 * 3; i++) {
    for (const wd of weekdays) {
      const hit = isoFromWeekdayOnOrAfter(cursor, wd, rule.interval, startDate);
      if (
        hit &&
        compareIso(hit, startDate) >= 0 &&
        compareIso(hit, afterDate) > 0 &&
        (!best || compareIso(hit, best) < 0)
      ) {
        best = hit;
      }
    }
    if (best) return best;
    cursor = addDays(cursor, 7);
  }
  return best;
}

/** First occurrence on or after startDate (inclusive). */
export function computeFirstRunDate(
  recurrence: RecurrenceRule,
  startDate: string,
  timezone: string,
): string {
  void timezone;
  const dayBefore = addDays(startDate, -1);
  const next = computeNextRunDate(recurrence, startDate, dayBefore);
  return next ?? startDate;
}

/** Next occurrence strictly after afterDate (afterDate may equal last occurrence). */
export function computeNextRunDate(
  recurrence: RecurrenceRule,
  startDate: string,
  afterDate: string,
): string | null {
  if (compareIso(afterDate, startDate) < 0) {
    afterDate = addDays(startDate, -1);
  }

  switch (recurrence.kind) {
    case "interval_days": {
      if (compareIso(afterDate, startDate) < 0) {
        return startDate;
      }
      return addDays(afterDate, recurrence.interval);
    }
    case "monthly_days":
      return nextMonthlyDays(recurrence, startDate, afterDate);
    case "monthly_boundary":
      return nextMonthlyBoundary(recurrence, startDate, afterDate);
    case "every_n_months":
      return nextEveryNMonths(recurrence, startDate, afterDate);
    case "every_n_weeks":
      return nextEveryNWeeks(recurrence, startDate, afterDate);
    default:
      return null;
  }
}

/** Next run on or after minDate (for restart). */
export function computeNextRunOnOrAfter(
  recurrence: RecurrenceRule,
  startDate: string,
  minDate: string,
  timezone: string,
): string | null {
  const dayBefore = addDays(minDate, -1);
  const first = computeFirstRunDate(recurrence, startDate, timezone);
  if (compareIso(first, minDate) >= 0) return first;
  return computeNextRunDate(recurrence, startDate, dayBefore);
}
