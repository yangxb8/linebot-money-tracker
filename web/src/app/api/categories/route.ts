import { NextResponse } from "next/server";
import {
  assertTenantL1Parent,
  ensureTenantTaxonomy,
  generateCustomCode,
  loadCategoryNodes,
  requireUser,
} from "@/lib/categories/server";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const tenantType = url.searchParams.get("tenant_type");
    const tenantId = url.searchParams.get("tenant_id");
    if (!tenantType || !tenantId) {
      return NextResponse.json(
        { error: "tenant_type and tenant_id required" },
        { status: 400 },
      );
    }

    const supabase = await requireUser();
    const before = await supabase
      .from("category_nodes")
      .select("id")
      .eq("tenant_type", tenantType)
      .eq("tenant_id", tenantId)
      .limit(1);

    await ensureTenantTaxonomy(tenantType, tenantId);
    const nodes = await loadCategoryNodes(tenantType, tenantId);

    return NextResponse.json({
      initialized: !(before.data?.length ?? 0),
      nodes,
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

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const tenantType = String(body.tenant_type ?? "");
    const tenantId = String(body.tenant_id ?? "");
    const level = Number(body.level);
    const nameJa = String(body.name_ja ?? "").trim();
    const parentId = body.parent_id ? String(body.parent_id) : null;

    if (!tenantType || !tenantId || !nameJa || (level !== 1 && level !== 2)) {
      return NextResponse.json({ error: "invalid_request" }, { status: 400 });
    }
    if (level === 2 && !parentId) {
      return NextResponse.json({ error: "parent_required" }, { status: 400 });
    }

    const supabase = await ensureTenantTaxonomy(tenantType, tenantId);

    if (level === 2 && parentId) {
      await assertTenantL1Parent(supabase, tenantType, tenantId, parentId);
    }

    let siblingQuery = supabase
      .from("category_nodes")
      .select("sort_order")
      .eq("tenant_type", tenantType)
      .eq("tenant_id", tenantId)
      .eq("level", level);

    siblingQuery =
      level === 1
        ? siblingQuery.is("parent_id", null)
        : siblingQuery.eq("parent_id", parentId);

    const { data: siblings } = await siblingQuery.order("sort_order", {
      ascending: false,
    });
    const sortOrder = (siblings?.[0]?.sort_order ?? 0) + 1;

    const { data, error } = await supabase
      .from("category_nodes")
      .insert({
        id: crypto.randomUUID(),
        code: generateCustomCode(),
        name_ja: nameJa,
        level,
        parent_id: level === 1 ? null : parentId,
        sort_order: sortOrder,
        tenant_type: tenantType,
        tenant_id: tenantId,
      })
      .select("id, code, name_ja, level, parent_id, sort_order")
      .single();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return NextResponse.json(
      {
        ...data,
        expense_count: 0,
        deletable: data.code !== "unknown",
      },
      { status: 201 },
    );
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
