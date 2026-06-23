import { NextResponse } from "next/server";
import {
  computeInitialNextRunDate,
  enrichSchedules,
  fetchLineUserId,
  mapScheduleRow,
  requirePeriodicUser,
  resolveCategoryAssignment,
} from "@/lib/periodic/server";
import { assertTenantAccess, parseTenantParams } from "@/lib/periodic/tenant-access";
import type { EndKind, RecurrenceRule } from "@/lib/periodic/types";
import { validateCreatePayload } from "@/lib/periodic/validation";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const { tenantType, tenantId } = parseTenantParams(
      url.searchParams.get("tenant_type"),
      url.searchParams.get("tenant_id"),
    );

    const supabase = await requirePeriodicUser();
    await assertTenantAccess(supabase, tenantType, tenantId);

    const { data, error } = await supabase
      .from("periodic_expense_schedules")
      .select("*")
      .eq("tenant_type", tenantType)
      .eq("tenant_id", tenantId)
      .order("next_run_date", { ascending: true, nullsFirst: false })
      .order("created_at", { ascending: false });

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    const rows = (data ?? []).map((row) =>
      mapScheduleRow(row as Record<string, unknown>),
    );
    const schedules = await enrichSchedules(rows);

    return NextResponse.json({ schedules });
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

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const tenantType = String(body.tenant_type ?? "");
    const tenantId = String(body.tenant_id ?? "");
    parseTenantParams(tenantType, tenantId);

    const validation = validateCreatePayload(body);
    if (!validation.ok) {
      return NextResponse.json({ error: validation.error }, { status: 400 });
    }

    const supabase = await requirePeriodicUser();
    await assertTenantAccess(supabase, tenantType, tenantId);
    const lineUserId = await fetchLineUserId(supabase);

    const categoryNodeId = String(body.category_node_id);
    const assignment = await resolveCategoryAssignment(
      tenantType,
      tenantId,
      categoryNodeId,
    );

    const recurrence = body.recurrence as RecurrenceRule;
    const startDate = String(body.start_date).slice(0, 10);
    const timezone = String(body.timezone ?? "Asia/Tokyo");
    const endKind = (body.end_kind as EndKind) ?? "never";

    const nextRunDate = computeInitialNextRunDate(recurrence, startDate, timezone);

    const { data, error } = await supabase
      .from("periodic_expense_schedules")
      .insert({
        tenant_type: tenantType,
        tenant_id: tenantId,
        name: String(body.name).trim(),
        amount: Number(body.amount),
        currency: "JPY",
        assigned_level: assignment.assigned_level,
        category_node_id: assignment.category_node_id,
        category_l1_id: assignment.category_l1_id,
        category_l2_id: assignment.category_l2_id,
        recurrence,
        start_date: startDate,
        timezone,
        end_kind: endKind,
        end_date: body.end_date ? String(body.end_date).slice(0, 10) : null,
        end_amount_cap:
          body.end_amount_cap != null ? Number(body.end_amount_cap) : null,
        end_repeat_limit:
          body.end_repeat_limit != null ? Number(body.end_repeat_limit) : null,
        status: "active",
        next_run_date: nextRunDate,
        created_by_line_user_id: lineUserId,
      })
      .select("*")
      .single();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    const [schedule] = await enrichSchedules([
      mapScheduleRow(data as Record<string, unknown>),
    ]);
    return NextResponse.json(schedule, { status: 201 });
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
