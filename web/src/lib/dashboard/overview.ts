import { computeBudgetHealth } from "@/lib/budget/health";
import type { BudgetCategoryNode, HealthTone } from "@/lib/budget/types";
import { computeNextRunDate } from "@/lib/periodic/recurrence";
import type {
  PeriodicScheduleResponse,
  RecurrenceRule,
} from "@/lib/periodic/types";

export type SpendSlice = {
  id: string;
  label: string;
  amount: number;
  pct: number;
};

export type MerchantSpend = {
  label: string;
  amount: number;
  count: number;
  pct: number;
};

export type UpcomingPeriodicItem = {
  id: string;
  name: string;
  amount: number;
  dates: string[];
};

export type LargestExpenseItem = {
  id: string;
  description: string;
  amount: number;
  expense_date: string;
  merchant_display: string | null;
  category_label: string | null;
};

const ATTENTION_TONES: ReadonlySet<HealthTone> = new Set(["caution", "bad"]);

/** L1 categories with a limit that are not on-track (caution / over pace). */
export function selectAttentionL1Categories(
  categories: BudgetCategoryNode[],
  elapsedDays: number,
  daysInMonth: number,
): BudgetCategoryNode[] {
  return categories
    .filter((node) => {
      if (!node.has_limit || node.limit == null || node.limit <= 0) return false;
      const health = computeBudgetHealth(
        node.spent_aggregate,
        node.limit,
        elapsedDays,
        daysInMonth,
      );
      return ATTENTION_TONES.has(health.tone);
    })
    .slice()
    .sort((a, b) => {
      const ha = computeBudgetHealth(
        a.spent_aggregate,
        a.limit,
        elapsedDays,
        daysInMonth,
      );
      const hb = computeBudgetHealth(
        b.spent_aggregate,
        b.limit,
        elapsedDays,
        daysInMonth,
      );
      if (ha.tone !== hb.tone) {
        return ha.tone === "bad" ? -1 : 1;
      }
      return (hb.paceRatio ?? 0) - (ha.paceRatio ?? 0);
    });
}

/**
 * Build percentage slices for an L1 spend distribution ring.
 * Zero-spend categories are omitted. When more than `maxSlices` categories
 * have spend, smaller ones collapse into an "Other" bucket.
 */
export function buildL1SpendSlices(
  categories: BudgetCategoryNode[],
  options?: { maxSlices?: number; otherLabel?: string },
): SpendSlice[] {
  const maxSlices = options?.maxSlices ?? 6;
  const otherLabel = options?.otherLabel ?? "Other";

  const positive = categories
    .map((node) => ({
      id: node.node_id,
      label: node.name_ja,
      amount: node.spent_aggregate,
    }))
    .filter((row) => row.amount > 0)
    .sort((a, b) => b.amount - a.amount);

  if (positive.length === 0) return [];

  let rows = positive;
  if (positive.length > maxSlices) {
    const head = positive.slice(0, maxSlices - 1);
    const rest = positive.slice(maxSlices - 1);
    const otherAmount = rest.reduce((sum, row) => sum + row.amount, 0);
    rows = [
      ...head,
      { id: "__other__", label: otherLabel, amount: otherAmount },
    ];
  }

  const total = rows.reduce((sum, row) => sum + row.amount, 0);
  if (total <= 0) return [];

  return rows.map((row) => ({
    ...row,
    pct: row.amount / total,
  }));
}

/** Fixed palette for the spend ring (matches existing dashboard neutrals + accents). */
export const SPEND_RING_COLORS = [
  "#0d9488",
  "#2563eb",
  "#ea580c",
  "#db2777",
  "#65a30d",
  "#0891b2",
  "#ca8a04",
  "#57534e",
] as const;

/** Yen left per day for the rest of the fiscal period. */
export function dailyRemainingAllowance(
  remaining: number | null,
  daysLeft: number,
): number | null {
  if (remaining == null || daysLeft <= 0) return null;
  return Math.floor(Math.max(0, remaining) / daysLeft);
}

export function shouldShowUnbudgeted(
  unbudgetedSpent: number,
  hasAnyLimit: boolean,
): boolean {
  return hasAnyLimit && unbudgetedSpent > 0;
}

/**
 * Rank merchant spend from expense rows that already have resolved
 * `merchant_display` labels. Rows without a merchant are skipped.
 */
export function buildTopMerchants(
  expenses: { merchant_display: string | null; amount: number }[],
  options?: { limit?: number },
): MerchantSpend[] {
  const limit = options?.limit ?? 5;
  const byLabel = new Map<string, { label: string; amount: number; count: number }>();

  for (const expense of expenses) {
    const label = expense.merchant_display?.trim();
    if (!label) continue;
    const key = label.toLocaleLowerCase();
    const existing = byLabel.get(key);
    if (existing) {
      existing.amount += expense.amount;
      existing.count += 1;
    } else {
      byLabel.set(key, { label, amount: expense.amount, count: 1 });
    }
  }

  const rows = Array.from(byLabel.values()).sort((a, b) => b.amount - a.amount);
  const top = rows.slice(0, limit);
  const total = top.reduce((sum, row) => sum + row.amount, 0);
  if (total <= 0) return [];

  return top.map((row) => ({
    ...row,
    pct: row.amount / total,
  }));
}

function collectRunsInPeriod(
  recurrence: RecurrenceRule,
  startDate: string,
  firstRun: string,
  periodEnd: string,
  hardEnd: string | null,
  maxRuns: number,
): string[] {
  const dates: string[] = [];
  let cursor: string | null = firstRun;
  while (cursor && dates.length < maxRuns) {
    if (cursor > periodEnd) break;
    if (hardEnd != null && cursor > hardEnd) break;
    dates.push(cursor);
    cursor = computeNextRunDate(recurrence, startDate, cursor);
  }
  return dates;
}

/**
 * Active periodic schedules with remaining runs in [fromDate, periodEnd].
 * Uses each schedule's stored next_run_date, then walks recurrence forward.
 */
export function selectUpcomingPeriodics(
  schedules: PeriodicScheduleResponse[],
  options: {
    periodEnd: string;
    fromDate: string;
    maxItems?: number;
    maxRunsPerSchedule?: number;
  },
): UpcomingPeriodicItem[] {
  const maxItems = options.maxItems ?? 5;
  const maxRunsPerSchedule = options.maxRunsPerSchedule ?? 8;
  const items: UpcomingPeriodicItem[] = [];

  for (const schedule of schedules) {
    if (schedule.status !== "active") continue;
    const first = schedule.next_run_date;
    if (!first || first < options.fromDate || first > options.periodEnd) {
      continue;
    }

    const hardEnd =
      schedule.end_kind === "on_date" && schedule.end_date
        ? schedule.end_date
        : null;

    const dates = collectRunsInPeriod(
      schedule.recurrence,
      schedule.start_date,
      first,
      options.periodEnd,
      hardEnd,
      maxRunsPerSchedule,
    );
    if (dates.length === 0) continue;

    items.push({
      id: schedule.id,
      name: schedule.name,
      amount: schedule.amount,
      dates,
    });
  }

  return items
    .sort((a, b) => {
      const byDate = a.dates[0]!.localeCompare(b.dates[0]!);
      if (byDate !== 0) return byDate;
      return a.name.localeCompare(b.name);
    })
    .slice(0, maxItems);
}

/**
 * Top expenses by amount, excluding rows created by periodic schedules.
 */
export function selectLargestNonPeriodicExpenses(
  expenses: {
    id: string;
    description: string;
    amount: number;
    expense_date: string;
    merchant_display: string | null;
    periodic_schedule_id: string | null;
    category_l2_name: string | null;
    category_l1_name: string | null;
    category_name_ja: string | null;
  }[],
  options?: { limit?: number },
): LargestExpenseItem[] {
  const limit = options?.limit ?? 5;
  return expenses
    .filter((row) => !row.periodic_schedule_id)
    .slice()
    .sort((a, b) => {
      if (b.amount !== a.amount) return b.amount - a.amount;
      return b.expense_date.localeCompare(a.expense_date);
    })
    .slice(0, limit)
    .map((row) => ({
      id: row.id,
      description: row.description,
      amount: row.amount,
      expense_date: row.expense_date,
      merchant_display: row.merchant_display,
      category_label:
        row.category_l2_name ??
        row.category_l1_name ??
        row.category_name_ja ??
        null,
    }));
}
