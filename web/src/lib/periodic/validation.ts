import type { EndKind, RecurrenceRule } from "@/lib/periodic/types";

export type ValidationResult = { ok: true } | { ok: false; error: string };

export function validateRecurrence(recurrence: unknown): ValidationResult {
  if (!recurrence || typeof recurrence !== "object") {
    return { ok: false, error: "invalid_recurrence" };
  }
  const r = recurrence as RecurrenceRule;
  switch (r.kind) {
    case "interval_days":
      if (!Number.isInteger(r.interval) || r.interval < 1) {
        return { ok: false, error: "invalid_interval" };
      }
      return { ok: true };
    case "monthly_days":
      if (!Array.isArray(r.days) || r.days.length === 0) {
        return { ok: false, error: "invalid_monthly_days" };
      }
      if (r.days.some((d) => !Number.isInteger(d) || d < 1 || d > 31)) {
        return { ok: false, error: "invalid_monthly_days" };
      }
      return { ok: true };
    case "monthly_boundary":
      if (r.boundary !== "first" && r.boundary !== "last") {
        return { ok: false, error: "invalid_boundary" };
      }
      return { ok: true };
    case "every_n_months":
      if (!Number.isInteger(r.interval) || r.interval < 1) {
        return { ok: false, error: "invalid_interval" };
      }
      if (!Number.isInteger(r.day) || r.day < 1 || r.day > 31) {
        return { ok: false, error: "invalid_day" };
      }
      return { ok: true };
    case "every_n_weeks":
      if (!Number.isInteger(r.interval) || r.interval < 1) {
        return { ok: false, error: "invalid_interval" };
      }
      if (!Array.isArray(r.weekdays) || r.weekdays.length === 0) {
        return { ok: false, error: "invalid_weekdays" };
      }
      if (r.weekdays.some((w) => !Number.isInteger(w) || w < 0 || w > 6)) {
        return { ok: false, error: "invalid_weekdays" };
      }
      return { ok: true };
    default:
      return { ok: false, error: "unknown_recurrence_kind" };
  }
}

export function validateEndCondition(
  endKind: EndKind,
  endDate?: string | null,
  endAmountCap?: number | null,
  endRepeatLimit?: number | null,
): ValidationResult {
  switch (endKind) {
    case "never":
      return { ok: true };
    case "on_date":
      if (!endDate) return { ok: false, error: "end_date_required" };
      return { ok: true };
    case "amount_cap":
      if (endAmountCap == null || endAmountCap <= 0) {
        return { ok: false, error: "end_amount_cap_required" };
      }
      return { ok: true };
    case "repeat_count":
      if (!endRepeatLimit || endRepeatLimit < 1) {
        return { ok: false, error: "end_repeat_limit_required" };
      }
      return { ok: true };
    default:
      return { ok: false, error: "invalid_end_kind" };
  }
}

export function validateCreatePayload(body: Record<string, unknown>): ValidationResult {
  const name = String(body.name ?? "").trim();
  if (!name) return { ok: false, error: "name_required" };

  const amount = Number(body.amount);
  if (!Number.isFinite(amount) || amount <= 0) {
    return { ok: false, error: "invalid_amount" };
  }

  const level = Number(body.assigned_level);
  if (level !== 1 && level !== 2) {
    return { ok: false, error: "invalid_assigned_level" };
  }

  if (!body.category_node_id) {
    return { ok: false, error: "category_required" };
  }

  if (!body.start_date) {
    return { ok: false, error: "start_date_required" };
  }

  const recurrenceCheck = validateRecurrence(body.recurrence);
  if (!recurrenceCheck.ok) return recurrenceCheck;

  const endKind = (body.end_kind as EndKind) ?? "never";
  const endCheck = validateEndCondition(
    endKind,
    body.end_date as string | null,
    body.end_amount_cap != null ? Number(body.end_amount_cap) : null,
    body.end_repeat_limit != null ? Number(body.end_repeat_limit) : null,
  );
  if (!endCheck.ok) return endCheck;

  return { ok: true };
}

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
