import { NextResponse } from "next/server";
import {
  createWishListItem,
  listWishListItems,
  parseTenantParams,
} from "@/lib/wish-list/server";
import type {
  WishListOrder,
  WishListSort,
  WishListStatus,
} from "@/lib/wish-list/types";
import { validateCreatePayload } from "@/lib/wish-list/validation";

function parseStatus(value: string | null): WishListStatus {
  if (value === "executed") return "executed";
  return "active";
}

function parseSort(value: string | null): WishListSort {
  if (value === "created" || value === "price") return value;
  return "priority";
}

function parseOrder(value: string | null): WishListOrder | undefined {
  if (value === "asc" || value === "desc") return value;
  return undefined;
}

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const { tenantType, tenantId } = parseTenantParams(
      url.searchParams.get("tenant_type"),
      url.searchParams.get("tenant_id"),
    );

    const items = await listWishListItems(
      { tenantType, tenantId },
      parseStatus(url.searchParams.get("status")),
      parseSort(url.searchParams.get("sort")),
      parseOrder(url.searchParams.get("order")),
    );

    return NextResponse.json({ items });
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
    const body = (await request.json()) as Record<string, unknown>;
    const tenantType = String(body.tenant_type ?? "");
    const tenantId = String(body.tenant_id ?? "");
    parseTenantParams(tenantType, tenantId);

    const validation = validateCreatePayload(body);
    if (!validation.ok) {
      return NextResponse.json({ error: validation.error }, { status: 400 });
    }

    const item = await createWishListItem({
      tenant_type: tenantType,
      tenant_id: tenantId,
      name: String(body.name).trim(),
      amount: Number(body.amount),
      category_node_id: String(body.category_node_id),
      product_url:
        body.product_url != null ? String(body.product_url).trim() : null,
    });

    return NextResponse.json(item, { status: 201 });
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
