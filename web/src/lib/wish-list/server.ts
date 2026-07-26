import { createClient } from "@/lib/supabase/server";
import { localTodayIso } from "@/lib/periodic/recurrence";
import {
  fetchLineUserId,
  resolveCategoryAssignment,
} from "@/lib/periodic/server";
import {
  assertTenantAccess,
  parseTenantParams,
} from "@/lib/periodic/tenant-access";
import type {
  CreateWishListPayload,
  ExecuteWishListPayload,
  UpdateWishListPayload,
  WishListExpenseSummary,
  WishListItem,
  WishListOrder,
  WishListSort,
  WishListStatus,
} from "@/lib/wish-list/types";

export { assertTenantAccess, fetchLineUserId, parseTenantParams, resolveCategoryAssignment };

export type WishListTenant = {
  tenantType: string;
  tenantId: string;
};

type InternalWishListItem = WishListItem & {
  tenant_type: string;
  tenant_id: string;
};

const WISH_LIST_SELECT =
  "id, tenant_type, tenant_id, name, amount, currency, category_node_id, product_url, sort_order, status, created_at, executed_expense_id";

export async function requireWishListUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    throw new Response("Unauthorized", { status: 401 });
  }
  return supabase;
}

export function mapWishListRow(row: Record<string, unknown>): InternalWishListItem {
  return {
    id: String(row.id),
    tenant_type: String(row.tenant_type),
    tenant_id: String(row.tenant_id),
    name: String(row.name),
    amount: Number(row.amount),
    currency: String(row.currency),
    category_node_id: String(row.category_node_id),
    category_name: null,
    product_url: row.product_url ? String(row.product_url) : null,
    sort_order: Number(row.sort_order),
    status: row.status as WishListStatus,
    created_at: String(row.created_at),
    executed_expense_id: row.executed_expense_id
      ? String(row.executed_expense_id)
      : null,
    expense: null,
  };
}

function publicItem(item: InternalWishListItem): WishListItem {
  return {
    id: item.id,
    name: item.name,
    amount: item.amount,
    currency: item.currency,
    category_node_id: item.category_node_id,
    category_name: item.category_name,
    product_url: item.product_url,
    sort_order: item.sort_order,
    status: item.status,
    created_at: item.created_at,
    executed_expense_id: item.executed_expense_id,
    expense: item.expense,
  };
}

export async function enrichItems(
  rows: InternalWishListItem[],
): Promise<WishListItem[]> {
  if (rows.length === 0) return [];

  const supabase = await requireWishListUser();
  const categoryIds = new Set(rows.map((row) => row.category_node_id));
  const expenseIds = rows
    .map((row) => row.executed_expense_id)
    .filter((id): id is string => Boolean(id));

  const expenseById = new Map<string, WishListExpenseSummary>();
  if (expenseIds.length > 0) {
    const { data, error } = await supabase
      .from("expenses")
      .select("id, description, amount, currency, expense_date, category_node_id")
      .in("id", expenseIds)
      .is("deleted_at", null);

    if (error) {
      throw new Response(error.message, { status: 400 });
    }

    for (const expense of data ?? []) {
      const categoryNodeId = String(expense.category_node_id);
      categoryIds.add(categoryNodeId);
      expenseById.set(String(expense.id), {
        id: String(expense.id),
        description: String(expense.description),
        amount: Number(expense.amount),
        currency: String(expense.currency),
        expense_date: String(expense.expense_date).slice(0, 10),
        category_node_id: categoryNodeId,
        category_name: null,
      });
    }
  }

  const { data: categories, error: categoryError } = await supabase
    .from("category_nodes")
    .select("id, name_ja")
    .in("id", [...categoryIds]);

  if (categoryError) {
    throw new Response(categoryError.message, { status: 400 });
  }

  const nameById = new Map(
    (categories ?? []).map((category: { id: string; name_ja: string }) => [
      category.id,
      category.name_ja,
    ]),
  );

  return rows.map((row) => {
    const expense = row.executed_expense_id
      ? (expenseById.get(row.executed_expense_id) ?? null)
      : null;
    const enrichedExpense = expense
      ? {
          ...expense,
          category_name: nameById.get(expense.category_node_id) ?? null,
        }
      : null;

    return publicItem({
      ...row,
      category_name: nameById.get(row.category_node_id) ?? null,
      expense: enrichedExpense,
    });
  });
}

function normalizeProductUrl(value: string | null | undefined): string | null {
  const trimmed = String(value ?? "").trim();
  return trimmed ? trimmed : null;
}

function defaultOrder(sort: WishListSort, order?: WishListOrder): WishListOrder {
  if (order) return order;
  return sort === "priority" ? "asc" : "desc";
}

export async function listWishListItems(
  tenant: WishListTenant,
  status: WishListStatus = "active",
  sort: WishListSort = "priority",
  order?: WishListOrder,
): Promise<WishListItem[]> {
  const supabase = await requireWishListUser();
  await assertTenantAccess(supabase, tenant.tenantType, tenant.tenantId);

  const ascending = defaultOrder(sort, order) === "asc";
  let query = supabase
    .from("wish_list_items")
    .select(WISH_LIST_SELECT)
    .eq("tenant_type", tenant.tenantType)
    .eq("tenant_id", tenant.tenantId)
    .eq("status", status)
    .is("deleted_at", null);

  if (sort === "created") {
    query = query
      .order("created_at", { ascending })
      .order("sort_order", { ascending: true });
  } else if (sort === "price") {
    query = query
      .order("amount", { ascending })
      .order("sort_order", { ascending: true });
  } else {
    query = query
      .order("sort_order", { ascending })
      .order("created_at", { ascending: true });
  }

  const { data, error } = await query;
  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  const rows = (data ?? []).map((row) =>
    mapWishListRow(row as Record<string, unknown>),
  );
  return enrichItems(rows);
}

async function loadWishListItem(
  id: string,
): Promise<{
  supabase: Awaited<ReturnType<typeof requireWishListUser>>;
  row: InternalWishListItem;
}> {
  const supabase = await requireWishListUser();
  const { data, error } = await supabase
    .from("wish_list_items")
    .select(WISH_LIST_SELECT)
    .eq("id", id)
    .is("deleted_at", null)
    .maybeSingle();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }
  if (!data) {
    throw new Response("not_found", { status: 404 });
  }

  const row = mapWishListRow(data as Record<string, unknown>);
  await assertTenantAccess(supabase, row.tenant_type, row.tenant_id);
  return { supabase, row };
}

export async function getWishListItemById(id: string): Promise<WishListItem> {
  const { row } = await loadWishListItem(id);
  const [item] = await enrichItems([row]);
  return item;
}

export async function createWishListItem(
  payload: CreateWishListPayload,
): Promise<WishListItem> {
  const supabase = await requireWishListUser();
  parseTenantParams(payload.tenant_type, payload.tenant_id);
  await assertTenantAccess(supabase, payload.tenant_type, payload.tenant_id);

  const [lineUserId, assignment] = await Promise.all([
    fetchLineUserId(supabase),
    resolveCategoryAssignment(
      payload.tenant_type,
      payload.tenant_id,
      payload.category_node_id,
    ),
  ]);

  const { data: lastActive, error: orderError } = await supabase
    .from("wish_list_items")
    .select("sort_order")
    .eq("tenant_type", payload.tenant_type)
    .eq("tenant_id", payload.tenant_id)
    .eq("status", "active")
    .is("deleted_at", null)
    .order("sort_order", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (orderError) {
    throw new Response(orderError.message, { status: 400 });
  }

  const sortOrder =
    lastActive?.sort_order != null ? Number(lastActive.sort_order) + 1 : 0;

  const { data, error } = await supabase
    .from("wish_list_items")
    .insert({
      tenant_type: payload.tenant_type,
      tenant_id: payload.tenant_id,
      name: payload.name.trim(),
      amount: payload.amount,
      currency: "JPY",
      assigned_level: assignment.assigned_level,
      category_node_id: assignment.category_node_id,
      category_l1_id: assignment.category_l1_id,
      category_l2_id: assignment.category_l2_id,
      category_l3_id: null,
      product_url: normalizeProductUrl(payload.product_url),
      sort_order: sortOrder,
      status: "active",
      created_by_line_user_id: lineUserId,
    })
    .select(WISH_LIST_SELECT)
    .single();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  const [item] = await enrichItems([mapWishListRow(data as Record<string, unknown>)]);
  return item;
}

export async function updateWishListItem(
  id: string,
  payload: UpdateWishListPayload,
): Promise<WishListItem> {
  const { supabase, row } = await loadWishListItem(id);
  if (row.status !== "active") {
    throw new Response("not_active", { status: 409 });
  }

  const patch: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (payload.name !== undefined) patch.name = payload.name.trim();
  if (payload.amount !== undefined) patch.amount = payload.amount;
  if (payload.product_url !== undefined) {
    patch.product_url = normalizeProductUrl(payload.product_url);
  }

  if (payload.category_node_id !== undefined) {
    const assignment = await resolveCategoryAssignment(
      row.tenant_type,
      row.tenant_id,
      payload.category_node_id,
    );
    patch.assigned_level = assignment.assigned_level;
    patch.category_node_id = assignment.category_node_id;
    patch.category_l1_id = assignment.category_l1_id;
    patch.category_l2_id = assignment.category_l2_id;
    patch.category_l3_id = null;
  }

  const { data, error } = await supabase
    .from("wish_list_items")
    .update(patch)
    .eq("id", id)
    .eq("status", "active")
    .is("deleted_at", null)
    .select(WISH_LIST_SELECT)
    .single();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  const [item] = await enrichItems([mapWishListRow(data as Record<string, unknown>)]);
  return item;
}

export async function softDeleteWishListItem(id: string): Promise<void> {
  const { supabase, row } = await loadWishListItem(id);
  if (row.status !== "active") {
    throw new Response("not_active", { status: 409 });
  }

  const now = new Date().toISOString();
  const { error } = await supabase
    .from("wish_list_items")
    .update({ deleted_at: now, updated_at: now })
    .eq("id", id)
    .eq("status", "active")
    .is("deleted_at", null);

  if (error) {
    throw new Response(error.message, { status: 400 });
  }
}

export async function reorderWishListItems(
  tenant: WishListTenant,
  orderedIds: string[],
): Promise<void> {
  const uniqueIds = new Set(orderedIds);
  if (uniqueIds.size !== orderedIds.length) {
    throw new Response("invalid_ordered_ids", { status: 400 });
  }

  const supabase = await requireWishListUser();
  await assertTenantAccess(supabase, tenant.tenantType, tenant.tenantId);

  const { data, error } = await supabase
    .from("wish_list_items")
    .select("id")
    .eq("tenant_type", tenant.tenantType)
    .eq("tenant_id", tenant.tenantId)
    .eq("status", "active")
    .is("deleted_at", null);

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  const activeIds = (data ?? []).map((row) => String(row.id));
  if (
    activeIds.length !== orderedIds.length ||
    activeIds.some((id) => !uniqueIds.has(id))
  ) {
    throw new Response("ordered_ids_mismatch", { status: 409 });
  }

  const updates = await Promise.all(
    orderedIds.map((id, sortOrder) =>
      supabase
        .from("wish_list_items")
        .update({ sort_order: sortOrder, updated_at: new Date().toISOString() })
        .eq("id", id)
        .eq("tenant_type", tenant.tenantType)
        .eq("tenant_id", tenant.tenantId)
        .eq("status", "active")
        .is("deleted_at", null),
    ),
  );

  const failed = updates.find((result) => result.error);
  if (failed?.error) {
    throw new Response(failed.error.message, { status: 400 });
  }
}

export async function executeWishListItem(
  id: string,
  payload: ExecuteWishListPayload,
): Promise<{ item: WishListItem; expense: WishListExpenseSummary }> {
  const { supabase, row } = await loadWishListItem(id);
  const { tenantType, tenantId } = parseTenantParams(
    payload.tenant_type,
    payload.tenant_id,
  );

  if (row.tenant_type !== tenantType || row.tenant_id !== tenantId) {
    throw new Response("Forbidden", { status: 403 });
  }
  if (row.status !== "active") {
    throw new Response("not_active", { status: 409 });
  }

  const name = payload.name?.trim() || row.name;
  const amount = payload.amount ?? row.amount;
  const categoryNodeId = payload.category_node_id || row.category_node_id;
  const expenseDate =
    payload.expense_date?.slice(0, 10) || localTodayIso("Asia/Tokyo");

  const [lineUserId, assignment] = await Promise.all([
    fetchLineUserId(supabase),
    resolveCategoryAssignment(tenantType, tenantId, categoryNodeId),
  ]);

  const { data: expenseRow, error: expenseError } = await supabase
    .from("expenses")
    .insert({
      tenant_type: tenantType,
      tenant_id: tenantId,
      line_user_id: lineUserId,
      logged_by_line_user_id: lineUserId,
      source_message_id: `web:${crypto.randomUUID()}`,
      line_item_index: 0,
      description: name,
      amount,
      currency: "JPY",
      expense_date: expenseDate,
      category_node_id: assignment.category_node_id,
      assigned_level: assignment.assigned_level,
      category_l1_id: assignment.category_l1_id,
      category_l2_id: assignment.category_l2_id,
      category_l3_id: null,
      wish_list_item_id: id,
    })
    .select("id, description, amount, currency, expense_date, category_node_id")
    .single();

  if (expenseError) {
    throw new Response(expenseError.message, { status: 400 });
  }

  const { data: updated, error: updateError } = await supabase
    .from("wish_list_items")
    .update({
      status: "executed",
      executed_expense_id: String(expenseRow.id),
      updated_at: new Date().toISOString(),
    })
    .eq("id", id)
    .eq("status", "active")
    .is("deleted_at", null)
    .select(WISH_LIST_SELECT)
    .single();

  if (updateError) {
    throw new Response(updateError.message, { status: 400 });
  }

  const [expenseCategory, [item]] = await Promise.all([
    supabase
      .from("category_nodes")
      .select("name_ja")
      .eq("id", String(expenseRow.category_node_id))
      .maybeSingle(),
    enrichItems([mapWishListRow(updated as Record<string, unknown>)]),
  ]);

  if (expenseCategory.error) {
    throw new Response(expenseCategory.error.message, { status: 400 });
  }

  const expense = {
    id: String(expenseRow.id),
    description: String(expenseRow.description),
    amount: Number(expenseRow.amount),
    currency: String(expenseRow.currency),
    expense_date: String(expenseRow.expense_date).slice(0, 10),
    category_node_id: String(expenseRow.category_node_id),
    category_name: expenseCategory.data?.name_ja
      ? String(expenseCategory.data.name_ja)
      : null,
  };

  return { item, expense };
}
