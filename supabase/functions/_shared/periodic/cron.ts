import type { SupabaseClient } from "jsr:@supabase/supabase-js@2";
import { localTodayIso, computeNextRunDate } from "./recurrence.ts";
import type { PeriodicScheduleRow, ProcessAction, RecurrenceRule } from "./types.ts";
import {
  shouldEndAfterOccurrence,
  shouldEndBeforeOccurrence,
} from "./validation.ts";

export function mapScheduleRow(row: Record<string, unknown>): PeriodicScheduleRow {
  return {
    id: String(row.id),
    tenant_type: String(row.tenant_type),
    tenant_id: String(row.tenant_id),
    name: String(row.name),
    amount: Number(row.amount),
    currency: String(row.currency),
    assigned_level: Number(row.assigned_level),
    category_node_id: String(row.category_node_id),
    category_l1_id: String(row.category_l1_id),
    category_l2_id: row.category_l2_id ? String(row.category_l2_id) : null,
    recurrence: row.recurrence as RecurrenceRule,
    start_date: String(row.start_date).slice(0, 10),
    timezone: String(row.timezone),
    end_kind: row.end_kind as PeriodicScheduleRow["end_kind"],
    end_date: row.end_date ? String(row.end_date).slice(0, 10) : null,
    end_amount_cap: row.end_amount_cap != null ? Number(row.end_amount_cap) : null,
    end_repeat_limit: row.end_repeat_limit != null ? Number(row.end_repeat_limit) : null,
    status: row.status as PeriodicScheduleRow["status"],
    pause_reason: row.pause_reason ? String(row.pause_reason) : null,
    next_run_date: row.next_run_date ? String(row.next_run_date).slice(0, 10) : null,
    occurrence_count: Number(row.occurrence_count),
    cumulative_amount: Number(row.cumulative_amount),
    created_by_line_user_id: String(row.created_by_line_user_id),
    created_at: String(row.created_at),
    updated_at: String(row.updated_at),
  };
}

export function buildProcessActions(
  schedules: PeriodicScheduleRow[],
  asOf = new Date(),
): ProcessAction[] {
  const actions: ProcessAction[] = [];

  for (const schedule of schedules) {
    if (schedule.status !== "active" || !schedule.next_run_date) continue;

    const localToday = localTodayIso(schedule.timezone, asOf);
    if (schedule.next_run_date > localToday) continue;

    const occurrenceDate = schedule.next_run_date;
    const amount = schedule.amount;

    if (
      shouldEndBeforeOccurrence(
        schedule.end_kind,
        schedule.end_date,
        schedule.end_amount_cap,
        schedule.end_repeat_limit,
        schedule.occurrence_count,
        schedule.cumulative_amount,
        amount,
        occurrenceDate,
      )
    ) {
      actions.push({
        schedule_id: schedule.id,
        occurrence_date: occurrenceDate,
        next_run_date: null,
        end: true,
        skip_occurrence: true,
      });
      continue;
    }

    const endAfter = shouldEndAfterOccurrence(
      schedule.end_kind,
      schedule.end_date,
      schedule.end_amount_cap,
      schedule.end_repeat_limit,
      schedule.occurrence_count,
      schedule.cumulative_amount,
      amount,
      occurrenceDate,
    );

    const nextRun = endAfter
      ? null
      : computeNextRunDate(
          schedule.recurrence as RecurrenceRule,
          schedule.start_date,
          occurrenceDate,
        );

    actions.push({
      schedule_id: schedule.id,
      occurrence_date: occurrenceDate,
      next_run_date: nextRun,
      end: endAfter || nextRun === null,
    });
  }

  return actions;
}

export async function runPeriodicCron(
  admin: SupabaseClient,
  asOf = new Date(),
) {
  const { data: rows, error } = await admin
    .from("periodic_expense_schedules")
    .select("*")
    .eq("status", "active")
    .not("next_run_date", "is", null);

  if (error) {
    throw error;
  }

  const schedules = (rows ?? []).map((row) =>
    mapScheduleRow(row as Record<string, unknown>)
  );
  const actions = buildProcessActions(schedules, asOf);

  if (actions.length === 0) {
    return { processed: 0, inserted: 0, skipped: 0, ended: 0 };
  }

  const payload = actions.map((a) => ({
    schedule_id: a.schedule_id,
    occurrence_date: a.occurrence_date,
    next_run_date: a.next_run_date ?? "",
    end: a.end,
    skip_occurrence: Boolean(a.skip_occurrence),
  }));

  const { data, error: rpcError } = await admin.rpc("process_due_periodic_schedules", {
    p_actions: payload,
  });

  if (rpcError) {
    throw rpcError;
  }

  return (data ?? {
    processed: 0,
    inserted: 0,
    skipped: 0,
    ended: 0,
  }) as { processed: number; inserted: number; skipped: number; ended: number };
}
