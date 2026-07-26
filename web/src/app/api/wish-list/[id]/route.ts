import { NextResponse } from "next/server";
import {
  softDeleteWishListItem,
  updateWishListItem,
} from "@/lib/wish-list/server";
import { validateUpdatePayload } from "@/lib/wish-list/validation";

type RouteParams = { params: Promise<{ id: string }> };

export async function PATCH(request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    const body = (await request.json()) as Record<string, unknown>;

    const validation = validateUpdatePayload(body);
    if (!validation.ok) {
      return NextResponse.json({ error: validation.error }, { status: 400 });
    }

    const item = await updateWishListItem(id, {
      name: body.name !== undefined ? String(body.name) : undefined,
      amount: body.amount !== undefined ? Number(body.amount) : undefined,
      category_node_id:
        body.category_node_id !== undefined
          ? String(body.category_node_id)
          : undefined,
      product_url:
        body.product_url !== undefined
          ? body.product_url == null
            ? null
            : String(body.product_url)
          : undefined,
    });

    return NextResponse.json(item);
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
    await softDeleteWishListItem(id);
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
