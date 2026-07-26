import { NextResponse } from "next/server";
import {
  parseTenantParams,
  reorderWishListItems,
} from "@/lib/wish-list/server";
import { validateReorderPayload } from "@/lib/wish-list/validation";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const tenantType = String(body.tenant_type ?? "");
    const tenantId = String(body.tenant_id ?? "");
    parseTenantParams(tenantType, tenantId);

    const validation = validateReorderPayload(body);
    if (!validation.ok) {
      return NextResponse.json({ error: validation.error }, { status: 400 });
    }

    await reorderWishListItems(
      { tenantType, tenantId },
      body.ordered_ids as string[],
    );

    return NextResponse.json({ ok: true });
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
