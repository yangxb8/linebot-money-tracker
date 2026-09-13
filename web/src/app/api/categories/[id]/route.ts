import { NextResponse } from "next/server";
import { hasCategoryNameConflict, requireUser } from "@/lib/categories/server";

type RouteContext = { params: Promise<{ id: string }> };

export async function PATCH(request: Request, context: RouteContext) {
  try {
    const { id } = await context.params;
    const body = await request.json();
    const payload: Record<string, string | number | boolean> = {};

    if (body.name_ja !== undefined) {
      const nameJa = String(body.name_ja).trim();
      if (!nameJa) {
        return NextResponse.json({ error: "name_required" }, { status: 400 });
      }
      payload.name_ja = nameJa;
    }
    if (body.sort_order !== undefined) {
      payload.sort_order = Number(body.sort_order);
    }
    if (body.pace_warning_enabled !== undefined) {
      payload.pace_warning_enabled = Boolean(body.pace_warning_enabled);
    }

    if (Object.keys(payload).length === 0) {
      return NextResponse.json({ error: "no_updates" }, { status: 400 });
    }

    const supabase = await requireUser();

    if (payload.name_ja !== undefined) {
      const { data: existing, error: fetchError } = await supabase
        .from("category_nodes")
        .select("tenant_type, tenant_id")
        .eq("id", id)
        .single();

      if (fetchError || !existing?.tenant_type || !existing?.tenant_id) {
        return NextResponse.json({ error: "not_found" }, { status: 404 });
      }

      if (
        await hasCategoryNameConflict(
          supabase,
          existing.tenant_type,
          existing.tenant_id,
          String(payload.name_ja),
          id,
        )
      ) {
        return NextResponse.json({ error: "duplicate_name" }, { status: 409 });
      }
    }

    const { data, error } = await supabase
      .from("category_nodes")
      .update(payload)
      .eq("id", id)
      .select("id, code, name_ja, level, parent_id, sort_order, pace_warning_enabled")
      .single();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return NextResponse.json({
      ...data,
      pace_warning_enabled: Boolean(data.pace_warning_enabled),
      expense_count: 0,
      deletable: data.code !== "unknown",
    });
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
