import { NextResponse } from "next/server";
import { requireUser } from "@/lib/categories/server";

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(request: Request, context: RouteContext) {
  try {
    const { id } = await context.params;
    const body = await request.json();
    const level = Number(body.level);
    const parentId = body.parent_id ? String(body.parent_id) : null;

    if (level !== 1 && level !== 2) {
      return NextResponse.json({ error: "invalid_level" }, { status: 400 });
    }
    if (level === 2 && !parentId) {
      return NextResponse.json({ error: "parent_required" }, { status: 400 });
    }
    if (level === 1 && parentId) {
      return NextResponse.json({ error: "parent_not_allowed" }, { status: 400 });
    }

    const supabase = await requireUser();
    const { data, error } = await supabase.rpc("move_category", {
      p_node_id: id,
      p_new_level: level,
      p_new_parent_id: parentId,
    });

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
