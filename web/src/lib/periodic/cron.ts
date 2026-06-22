import { createAdminClient } from "@/lib/supabase/admin";
import { localTodayIso, computeNextRunDate } from "@/lib/periodic/recurrence";
import type { PeriodicScheduleRow, ProcessAction, RecurrenceRule } from "@/lib/periodic/types";
import {
  shouldEndAfterOccurrence,
  shouldEndBeforeOccurrence,
} from "@/lib/periodic/validation";
import { mapScheduleRow } from "@/lib/periodic/server";

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

export async function runPeriodicCron(asOf = new Date()) {
  const admin = createAdminClient();
  const { data: rows, error } = await admin
    .from("periodic_expense_schedules")
    .select("*")
    .eq("status", "active")
    .not("next_run_date", "is", null);

  if (error) {
    throw error;
  }

  const schedules = (rows ?? []).map((row) => mapScheduleRow(row as Record<string, unknown>));
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
