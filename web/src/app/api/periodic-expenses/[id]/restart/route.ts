import { NextResponse } from "next/server";
import {
  computeNextRunAfterEdit,
  enrichSchedules,
  mapScheduleRow,
  requirePeriodicUser,
} from "@/lib/periodic/server";
import { assertTenantAccess } from "@/lib/periodic/tenant-access";
import type { EndKind, RecurrenceRule } from "@/lib/periodic/types";
import { localTodayIso } from "@/lib/periodic/recurrence";
import { validateEndCondition } from "@/lib/periodic/validation";

type RouteParams = { params: Promise<{ id: string }> };

export async function POST(request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    const body = await request.json().catch(() => ({}));
    const supabase = await requirePeriodicUser();

    const { data: existing, error: fetchError } = await supabase
      .from("periodic_expense_schedules")
      .select("*")
      .eq("id", id)
      .maybeSingle();

    if (fetchError) {
      return NextResponse.json({ error: fetchError.message }, { status: 400 });
    }
    if (!existing) {
      return NextResponse.json({ error: "not_found" }, { status: 404 });
    }

    const row = mapScheduleRow(existing as Record<string, unknown>);
    await assertTenantAccess(supabase, row.tenant_type, row.tenant_id);

    if (row.pause_reason === "category_missing") {
      return NextResponse.json({ error: "category_missing" }, { status: 409 });
    }

    if (row.status === "active") {
      return NextResponse.json({ error: "already_active" }, { status: 409 });
    }

    if (row.status === "ended") {
      const endKind = (body.end_kind as EndKind) ?? row.end_kind;
      const endDate =
        body.end_date !== undefined
          ? body.end_date
            ? String(body.end_date).slice(0, 10)
            : null
          : row.end_date;
      const endAmountCap =
        body.end_amount_cap !== undefined
          ? body.end_amount_cap != null
            ? Number(body.end_amount_cap)
            : null
          : row.end_amount_cap;
      const endRepeatLimit =
        body.end_repeat_limit !== undefined
          ? body.end_repeat_limit != null
            ? Number(body.end_repeat_limit)
            : null
          : row.end_repeat_limit;

      const unchanged =
        endKind === row.end_kind &&
        endDate === row.end_date &&
        endAmountCap === row.end_amount_cap &&
        endRepeatLimit === row.end_repeat_limit;

      if (unchanged) {
        return NextResponse.json({ error: "end_conditions_unchanged" }, { status: 409 });
      }

      const endCheck = validateEndCondition(
        endKind,
        endDate,
        endAmountCap,
        endRepeatLimit,
      );
      if (!endCheck.ok) {
        return NextResponse.json({ error: endCheck.error }, { status: 400 });
      }

      row.end_kind = endKind;
      row.end_date = endDate;
      row.end_amount_cap = endAmountCap;
      row.end_repeat_limit = endRepeatLimit;
    }

    const today = localTodayIso(row.timezone);
    const nextRun = computeNextRunAfterEdit(
      row.recurrence as RecurrenceRule,
      row.start_date,
      row.timezone,
      today,
    );

    if (!nextRun) {
      return NextResponse.json({ error: "no_future_occurrence" }, { status: 400 });
    }

    const patch: Record<string, unknown> = {
      status: "active",
      pause_reason: null,
      next_run_date: nextRun,
      updated_at: new Date().toISOString(),
    };

    if (row.status === "ended") {
      patch.end_kind = row.end_kind;
      patch.end_date = row.end_date;
      patch.end_amount_cap = row.end_amount_cap;
      patch.end_repeat_limit = row.end_repeat_limit;
    }

    const { data, error } = await supabase
      .from("periodic_expense_schedules")
      .update(patch)
      .eq("id", id)
      .select("*")
      .single();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    const [schedule] = await enrichSchedules([
      mapScheduleRow(data as Record<string, unknown>),
    ]);
    return NextResponse.json(schedule);
  } catch (error) {
    if (error instanceof Response) {
      return NextResponse.json(
        { error: await error.text() },
        { status: error.status },
      );
    }
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
