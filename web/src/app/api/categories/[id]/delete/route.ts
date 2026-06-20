import { NextResponse } from "next/server";
import { requireUser } from "@/lib/categories/server";

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(request: Request, context: RouteContext) {
  try {
    const { id } = await context.params;
    const body = await request.json();
    const transferToId = body.transfer_to_id
      ? String(body.transfer_to_id)
      : null;

    const supabase = await requireUser();
    const { data, error } = await supabase.rpc("delete_category_with_transfer", {
      p_node_id: id,
      p_transfer_to_id: transferToId,
    });

    if (error) {
      const message = error.message.includes("transfer_required")
        ? "このカテゴリには支出があります。移行先を選択してください。"
        : error.message;
      return NextResponse.json(
        {
          error: error.message.includes("transfer_required")
            ? "transfer_required"
            : "delete_failed",
          message,
        },
        { status: 400 },
      );
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
