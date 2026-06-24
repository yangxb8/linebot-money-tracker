import { createClient } from "@/lib/supabase/server";
import type { CategoryNode } from "@/lib/categories/types";

type DbNode = {
  id: string;
  code: string;
  name_ja: string;
  level: number;
  parent_id: string | null;
  sort_order: number;
};

export async function requireUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    throw new Response("Unauthorized", { status: 401 });
  }
  return supabase;
}

export async function ensureTenantTaxonomy(
  tenantType: string,
  tenantId: string,
) {
  const supabase = await requireUser();
  const { error } = await supabase.rpc("ensure_tenant_taxonomy", {
    p_tenant_type: tenantType,
    p_tenant_id: tenantId,
  });
  if (error) {
    throw new Response(error.message, { status: 400 });
  }
  return supabase;
}

export async function loadCategoryNodes(
  tenantType: string,
  tenantId: string,
): Promise<CategoryNode[]> {
  const supabase = await ensureTenantTaxonomy(tenantType, tenantId);

  const { data: nodes, error } = await supabase
    .from("category_nodes")
    .select("id, code, name_ja, level, parent_id, sort_order")
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId)
    .order("level")
    .order("sort_order");

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  const { data: expenses, error: expenseError } = await supabase
    .from("expenses")
    .select("category_node_id, category_l1_id, category_l2_id")
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId)
    .is("deleted_at", null);

  if (expenseError) {
    throw new Response(expenseError.message, { status: 400 });
  }

  const counts = new Map<string, number>();
  for (const row of expenses ?? []) {
    const nodeId = row.category_node_id as string;
    counts.set(nodeId, (counts.get(nodeId) ?? 0) + 1);
    const l1Id = row.category_l1_id as string;
    if (l1Id && l1Id !== nodeId) {
      counts.set(l1Id, (counts.get(l1Id) ?? 0) + 1);
    }
  }

  const l1Count = (nodes ?? []).filter((n) => n.level === 1).length;

  return (nodes ?? []).map((node: DbNode) => {
    const expenseCount = counts.get(node.id) ?? 0;
    const deletable =
      node.code !== "unknown" && !(node.level === 1 && l1Count <= 1);
    return {
      id: node.id,
      code: node.code,
      name_ja: node.name_ja,
      level: node.level as 1 | 2,
      parent_id: node.parent_id,
      sort_order: node.sort_order,
      expense_count: expenseCount,
      deletable,
    };
  });
}

export function generateCustomCode(): string {
  const hex = crypto.randomUUID().replace(/-/g, "").slice(0, 8);
  return `custom.${hex}`;
}

export async function assertTenantL1Parent(
  supabase: Awaited<ReturnType<typeof requireUser>>,
  tenantType: string,
  tenantId: string,
  parentId: string,
) {
  const { data: parent, error } = await supabase
    .from("category_nodes")
    .select("id, level, tenant_type, tenant_id")
    .eq("id", parentId)
    .single();

  if (error || !parent) {
    throw new Response("parent_not_found", { status: 400 });
  }
  if (
    parent.level !== 1 ||
    parent.tenant_type !== tenantType ||
    parent.tenant_id !== tenantId
  ) {
    throw new Response("invalid_parent", { status: 400 });
  }
}

export async function hasCategoryNameConflict(
  supabase: Awaited<ReturnType<typeof requireUser>>,
  tenantType: string,
  tenantId: string,
  nameJa: string,
  excludeId?: string,
): Promise<boolean> {
  const normalized = nameJa.trim();
  const { data, error } = await supabase
    .from("category_nodes")
    .select("id, name_ja")
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId);

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  return (data ?? []).some(
    (row) =>
      row.id !== excludeId && String(row.name_ja).trim() === normalized,
  );
}
