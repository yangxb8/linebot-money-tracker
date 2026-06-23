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

export function currentBudgetMonthJst(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(new Date());
  const year = parts.find((p) => p.type === "year")?.value ?? "1970";
  const month = parts.find((p) => p.type === "month")?.value ?? "01";
  return `${year}-${month}-01`;
}

export function isCurrentBudgetMonth(budgetMonth: string): boolean {
  return budgetMonth === currentBudgetMonthJst();
}

export function shiftBudgetMonth(budgetMonth: string, deltaMonths: number): string {
  const [y, m] = budgetMonth.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + deltaMonths, 1));
  const year = d.getUTCFullYear();
  const month = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${year}-${month}-01`;
}
