import { computeBudgetHealth } from "@/lib/budget/health";
import type { BudgetCategoryNode, HealthTone } from "@/lib/budget/types";

export type SpendSlice = {
  id: string;
  label: string;
  amount: number;
  pct: number;
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
