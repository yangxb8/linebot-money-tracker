import type { Locale } from "@/lib/i18n/messages";

export function formatYen(amount: number, locale: Locale = "ja"): string {
  const loc = locale === "zh" ? "zh-CN" : locale === "en" ? "en-US" : "ja-JP";
  return new Intl.NumberFormat(loc, {
    style: "currency",
    currency: "JPY",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatPercent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

export function formatDailyAllowance(
  remaining: number,
  daysLeft: number,
  formatYenFn: (n: number) => string,
): string {
  if (daysLeft <= 0) return formatYenFn(0);
  const perDay = Math.max(0, Math.floor(remaining / daysLeft));
  return formatYenFn(perDay);
}

export function getTodayJst(): { year: number; month: number; day: number } {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  return {
    year: Number(parts.find((p) => p.type === "year")?.value ?? 1970),
    month: Number(parts.find((p) => p.type === "month")?.value ?? 1),
    day: Number(parts.find((p) => p.type === "day")?.value ?? 1),
  };
}

export function fiscalPeriodStartForDate(
  year: number,
  month: number,
  day: number,
  fiscalStartDay = 1,
): string {
  let startYear = year;
  let startMonth = month;
  if (day < fiscalStartDay) {
    const prev = new Date(Date.UTC(year, month - 1, 1));
    prev.setUTCMonth(prev.getUTCMonth() - 1);
    startYear = prev.getUTCFullYear();
    startMonth = prev.getUTCMonth() + 1;
  }
  const start = new Date(Date.UTC(startYear, startMonth - 1, fiscalStartDay));
  const y = start.getUTCFullYear();
  const m = String(start.getUTCMonth() + 1).padStart(2, "0");
  const d = String(start.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function currentBudgetMonthJst(fiscalStartDay = 1): string {
  const today = getTodayJst();
  return fiscalPeriodStartForDate(
    today.year,
    today.month,
    today.day,
    fiscalStartDay,
  );
}

export function isCurrentBudgetMonth(
  budgetMonth: string,
  fiscalStartDay = 1,
): boolean {
  return budgetMonth === currentBudgetMonthJst(fiscalStartDay);
}

export function shiftBudgetMonth(budgetMonth: string, deltaMonths: number): string {
  const [y, m, d] = budgetMonth.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1 + deltaMonths, d));
  const year = next.getUTCFullYear();
  const month = String(next.getUTCMonth() + 1).padStart(2, "0");
  const day = String(next.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function fiscalPeriodEnd(budgetMonth: string): string {
  const [y, m, d] = budgetMonth.split("-").map(Number);
  const end = new Date(Date.UTC(y, m - 1 + 1, d - 1));
  const year = end.getUTCFullYear();
  const month = String(end.getUTCMonth() + 1).padStart(2, "0");
  const day = String(end.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatBudgetPeriodLabel(
  budgetMonth: string,
  fiscalPeriodEndDate?: string,
  fiscalStartDay = 1,
): string {
  if (fiscalStartDay === 1) {
    return budgetMonth.slice(0, 7);
  }
  const end = fiscalPeriodEndDate ?? fiscalPeriodEnd(budgetMonth);
  const short = (date: string) => {
    const [, month, day] = date.split("-");
    return `${Number(month)}/${Number(day)}`;
  };
  return `${short(budgetMonth)} – ${short(end)}`;
}
