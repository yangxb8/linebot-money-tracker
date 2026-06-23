import type { HealthResult } from "@/lib/budget/types";

export function computeBudgetHealth(
  spent: number,
  limit: number | null,
  elapsedDays: number,
  daysInMonth: number,
): HealthResult {
  const timePct =
    daysInMonth > 0
      ? Math.min(1, Math.max(0, elapsedDays / daysInMonth))
      : 0;

  if (limit == null || limit <= 0) {
    return {
      spentPct: null,
      timePct,
      paceRatio: null,
      tone: "neutral",
      labelKey: "budgetPaceNeutral",
    };
  }

  const spentPct = spent / limit;

  if (elapsedDays <= 1) {
    return {
      spentPct,
      timePct: Math.max(timePct, 1 / Math.max(daysInMonth, 1)),
      paceRatio: null,
      tone: "neutral",
      labelKey: "budgetPaceNeutral",
    };
  }

  if (timePct <= 0) {
    return {
      spentPct,
      timePct: Math.max(timePct, 1 / Math.max(daysInMonth, 1)),
      paceRatio: null,
      tone: "neutral",
      labelKey: "budgetPaceNeutral",
    };
  }

  const paceRatio = spentPct / timePct;

  if (paceRatio <= 1) {
    return {
      spentPct,
      timePct,
      paceRatio,
      tone: "good",
      labelKey: "budgetPaceOnTrack",
    };
  }

  if (paceRatio <= 1.25) {
    return {
      spentPct,
      timePct,
      paceRatio,
      tone: "caution",
      labelKey: "budgetPaceCaution",
    };
  }

  return {
    spentPct,
    timePct,
    paceRatio,
    tone: "bad",
    labelKey: "budgetPaceOver",
  };
}

export function healthToneClass(tone: HealthResult["tone"]): string {
  switch (tone) {
    case "good":
      return "text-emerald-700 bg-emerald-50";
    case "caution":
      return "text-amber-700 bg-amber-50";
    case "bad":
      return "text-red-700 bg-red-50";
    default:
      return "text-gray-600 bg-gray-50";
  }
}

export function progressBarClass(tone: HealthResult["tone"]): string {
  switch (tone) {
    case "good":
      return "bg-emerald-500";
    case "caution":
      return "bg-amber-500";
    case "bad":
      return "bg-red-500";
    default:
      return "bg-gray-400";
  }
}
