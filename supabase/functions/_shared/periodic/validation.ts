import type { EndKind } from "./types.ts";

export function shouldEndBeforeOccurrence(
  endKind: EndKind,
  endDate: string | null,
  endAmountCap: number | null,
  endRepeatLimit: number | null,
  occurrenceCount: number,
  cumulativeAmount: number,
  amount: number,
  occurrenceDate: string,
): boolean {
  if (endKind === "on_date" && endDate && occurrenceDate > endDate) {
    return true;
  }
  if (endKind === "repeat_count" && endRepeatLimit != null) {
    if (occurrenceCount >= endRepeatLimit) return true;
  }
  if (endKind === "amount_cap" && endAmountCap != null) {
    if (cumulativeAmount + amount > endAmountCap) return true;
  }
  return false;
}

export function shouldEndAfterOccurrence(
  endKind: EndKind,
  endDate: string | null,
  endAmountCap: number | null,
  endRepeatLimit: number | null,
  occurrenceCount: number,
  cumulativeAmount: number,
  amount: number,
  occurrenceDate: string,
): boolean {
  if (endKind === "on_date" && endDate && occurrenceDate >= endDate) {
    return true;
  }
  if (endKind === "repeat_count" && endRepeatLimit != null) {
    if (occurrenceCount + 1 >= endRepeatLimit) return true;
  }
  if (endKind === "amount_cap" && endAmountCap != null) {
    if (cumulativeAmount + amount >= endAmountCap) return true;
  }
  return false;
}
