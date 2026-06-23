import type { Locale } from "@/lib/i18n/messages";
import type { EndKind, RecurrenceRule, ScheduleStatus } from "@/lib/periodic/types";

const WEEKDAY_SHORT: Record<Locale, string[]> = {
  ja: ["日", "月", "火", "水", "木", "金", "土"],
  en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  zh: ["日", "一", "二", "三", "四", "五", "六"],
};

function ordinal(n: number, locale: Locale): string {
  if (locale === "ja") return `${n}日`;
  if (locale === "zh") return `${n}日`;
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
}

export function formatRecurrenceSummary(
  recurrence: RecurrenceRule,
  locale: Locale = "ja",
): string {
  switch (recurrence.kind) {
    case "interval_days":
      if (locale === "ja") return `${recurrence.interval}日ごと`;
      if (locale === "zh") return `每${recurrence.interval}天`;
      return `Every ${recurrence.interval} days`;
    case "monthly_days": {
      const days = recurrence.days
        .slice()
        .sort((a, b) => a - b)
        .map((d) => ordinal(d, locale))
        .join(locale === "en" ? " & " : "・");
      if (locale === "ja") return `毎月 ${days}`;
      if (locale === "zh") return `每月 ${days}`;
      return `Monthly on ${days}`;
    }
    case "monthly_boundary":
      if (recurrence.boundary === "first") {
        if (locale === "ja") return "毎月初";
        if (locale === "zh") return "每月初";
        return "First of month";
      }
      if (locale === "ja") return "毎月末";
      if (locale === "zh") return "每月末";
      return "Last of month";
    case "every_n_months": {
      const day = ordinal(recurrence.day, locale);
      if (locale === "ja") return `${recurrence.interval}ヶ月ごと ${day}`;
      if (locale === "zh") return `每${recurrence.interval}个月 ${day}`;
      return `Every ${recurrence.interval} months on ${day}`;
    }
    case "every_n_weeks": {
      const wd = recurrence.weekdays
        .slice()
        .sort((a, b) => a - b)
        .map((w) => WEEKDAY_SHORT[locale][w])
        .join(locale === "en" ? ", " : "・");
      if (locale === "ja") return `${recurrence.interval}週ごと ${wd}`;
      if (locale === "zh") return `每${recurrence.interval}周 ${wd}`;
      return `Every ${recurrence.interval} weeks on ${wd}`;
    }
    default:
      return "";
  }
}

export function formatStatusLabel(status: ScheduleStatus, locale: Locale): string {
  if (status === "paused") {
        if (locale === "ja") return "一時停止";
        if (locale === "zh") return "已暂停";
        return "Paused";
  }
  if (status === "ended") {
        if (locale === "ja") return "終了";
        if (locale === "zh") return "已结束";
        return "Ended";
  }
  if (locale === "ja") return "有効";
  if (locale === "zh") return "进行中";
  return "Active";
}

export function formatEndKindLabel(endKind: EndKind, locale: Locale): string {
  const map: Record<EndKind, Record<Locale, string>> = {
    never: { ja: "なし", en: "Never", zh: "无" },
    on_date: { ja: "日付で終了", en: "End on date", zh: "按日期结束" },
    amount_cap: { ja: "金額上限", en: "Amount cap", zh: "金额上限" },
    repeat_count: { ja: "回数上限", en: "Repeat limit", zh: "次数上限" },
  };
  return map[endKind][locale];
}

export function formatYen(amount: number): string {
  return `¥${Math.round(amount).toLocaleString("ja-JP")}`;
}
