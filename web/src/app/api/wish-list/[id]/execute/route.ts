import { NextResponse } from "next/server";
import {
  executeWishListItem,
  parseTenantParams,
} from "@/lib/wish-list/server";
import { validateExecutePayload } from "@/lib/wish-list/validation";

type RouteParams = { params: Promise<{ id: string }> };

export async function POST(request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    const body = (await request.json()) as Record<string, unknown>;
    const tenantType = String(body.tenant_type ?? "");
    const tenantId = String(body.tenant_id ?? "");
    parseTenantParams(tenantType, tenantId);

    const validation = validateExecutePayload(body);
    if (!validation.ok) {
      return NextResponse.json({ error: validation.error }, { status: 400 });
    }

    const result = await executeWishListItem(id, {
      tenant_type: tenantType,
      tenant_id: tenantId,
      name: body.name !== undefined ? String(body.name) : undefined,
      amount: body.amount !== undefined ? Number(body.amount) : undefined,
      category_node_id:
        body.category_node_id !== undefined
          ? String(body.category_node_id)
          : undefined,
      expense_date:
        body.expense_date !== undefined ? String(body.expense_date) : undefined,
    });

    return NextResponse.json(result);
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
