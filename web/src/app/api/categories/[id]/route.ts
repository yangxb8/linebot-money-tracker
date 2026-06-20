import { NextResponse } from "next/server";
import { requireUser } from "@/lib/categories/server";

type RouteContext = { params: Promise<{ id: string }> };

export async function PATCH(request: Request, context: RouteContext) {
  try {
    const { id } = await context.params;
    const body = await request.json();
    const payload: Record<string, string | number> = {};

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

    if (Object.keys(payload).length === 0) {
      return NextResponse.json({ error: "no_updates" }, { status: 400 });
    }

    const supabase = await requireUser();
    const { data, error } = await supabase
      .from("category_nodes")
      .update(payload)
      .eq("id", id)
      .select("id, code, name_ja, level, parent_id, sort_order")
      .single();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return NextResponse.json({
      ...data,
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
