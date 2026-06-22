import { NextResponse } from "next/server";
import {
  computeNextRunAfterEdit,
  enrichSchedules,
  mapScheduleRow,
  requirePeriodicUser,
  resolveCategoryAssignment,
} from "@/lib/periodic/server";
import { assertTenantAccess } from "@/lib/periodic/tenant-access";
import type { EndKind, RecurrenceRule } from "@/lib/periodic/types";
import { localTodayIso } from "@/lib/periodic/recurrence";
import { validateEndCondition } from "@/lib/periodic/validation";

type RouteParams = { params: Promise<{ id: string }> };

async function loadSchedule(id: string) {
  const supabase = await requirePeriodicUser();
  const { data, error } = await supabase
    .from("periodic_expense_schedules")
    .select("*")
    .eq("id", id)
    .maybeSingle();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }
  if (!data) {
    throw new Response("not_found", { status: 404 });
  }

  const row = mapScheduleRow(data as Record<string, unknown>);
  await assertTenantAccess(supabase, row.tenant_type, row.tenant_id);
  return { supabase, row };
}

export async function GET(_request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    const { row } = await loadSchedule(id);
    const [schedule] = await enrichSchedules([row]);
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

export async function PATCH(request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { supabase, row } = await loadSchedule(id);

    const patch: Record<string, unknown> = { updated_at: new Date().toISOString() };

    if (body.name != null) patch.name = String(body.name).trim();
    if (body.amount != null) {
      const amount = Number(body.amount);
      if (!Number.isFinite(amount) || amount <= 0) {
        return NextResponse.json({ error: "invalid_amount" }, { status: 400 });
      }
      patch.amount = amount;
    }

    let recurrence = row.recurrence as RecurrenceRule;
    if (body.recurrence) recurrence = body.recurrence as RecurrenceRule;
    if (body.recurrence) patch.recurrence = recurrence;

    let startDate = row.start_date;
    if (body.start_date) startDate = String(body.start_date).slice(0, 10);
    if (body.start_date) patch.start_date = startDate;

    let timezone = row.timezone;
    if (body.timezone) timezone = String(body.timezone);
    if (body.timezone) patch.timezone = timezone;

    let endKind = row.end_kind as EndKind;
    if (body.end_kind) endKind = body.end_kind as EndKind;
    if (body.end_kind) patch.end_kind = endKind;

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

    if (body.end_date !== undefined) patch.end_date = endDate;
    if (body.end_amount_cap !== undefined) patch.end_amount_cap = endAmountCap;
    if (body.end_repeat_limit !== undefined) patch.end_repeat_limit = endRepeatLimit;

    const endCheck = validateEndCondition(endKind, endDate, endAmountCap, endRepeatLimit);
    if (!endCheck.ok) {
      return NextResponse.json({ error: endCheck.error }, { status: 400 });
    }

    if (body.category_node_id) {
      const assignment = await resolveCategoryAssignment(
        row.tenant_type,
        row.tenant_id,
        String(body.category_node_id),
      );
      patch.assigned_level = assignment.assigned_level;
      patch.category_node_id = assignment.category_node_id;
      patch.category_l1_id = assignment.category_l1_id;
      patch.category_l2_id = assignment.category_l2_id;
      if (row.pause_reason === "category_missing") {
        patch.pause_reason = null;
      }
    }

    const reactivate = Boolean(body.reactivate);
    const today = localTodayIso(timezone);
    const nextRun = computeNextRunAfterEdit(recurrence, startDate, timezone, today);

    if (row.status === "ended" && reactivate) {
      patch.status = "active";
      patch.next_run_date = nextRun;
    } else if (row.status !== "ended") {
      patch.next_run_date = nextRun;
    }

    if (row.status === "paused" && body.reactivate) {
      patch.status = "active";
      patch.pause_reason = null;
      patch.next_run_date = nextRun;
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

export async function DELETE(_request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    const { supabase } = await loadSchedule(id);
    const { error } = await supabase
      .from("periodic_expense_schedules")
      .delete()
      .eq("id", id);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return new NextResponse(null, { status: 204 });
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
