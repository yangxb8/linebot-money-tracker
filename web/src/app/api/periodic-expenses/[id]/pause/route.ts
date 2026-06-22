import { NextResponse } from "next/server";
import { mapScheduleRow, requirePeriodicUser } from "@/lib/periodic/server";
import { assertTenantAccess } from "@/lib/periodic/tenant-access";

type RouteParams = { params: Promise<{ id: string }> };

export async function POST(_request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
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

    if (row.status === "paused") {
      return NextResponse.json({ error: "already_paused" }, { status: 409 });
    }
    if (row.status === "ended") {
      return NextResponse.json({ error: "already_ended" }, { status: 409 });
    }

    const { data, error } = await supabase
      .from("periodic_expense_schedules")
      .update({
        status: "paused",
        pause_reason: "user",
        updated_at: new Date().toISOString(),
      })
      .eq("id", id)
      .select("status, pause_reason")
      .single();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return NextResponse.json(data);
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
