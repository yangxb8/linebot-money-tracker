import { createClient } from "@/lib/supabase/server";
import { fiscalPeriodEnd } from "@/lib/budget/format";
import { resolveExpenseMerchantDisplay } from "@/lib/expenses/merchant.server";
import { resolveCategoryAssignment } from "@/lib/periodic/server";
import {
  assertTenantAccess,
  parseTenantParams,
} from "@/lib/periodic/tenant-access";
import type {
  CreateExpensePayload,
  ExpenseRecord,
  FiscalMonthOption,
  UpdateExpensePayload,
} from "@/lib/expenses/types";
import type { ExpenseListSort } from "@/lib/expenses/sort-group";
import { DEFAULT_EXPENSE_LIST_SORT } from "@/lib/expenses/sort-group";

export { parseTenantParams };

const EXPENSE_SELECT =
  "id, expense_date, description, amount, currency, category_node_id, category_name_ja, category_l1_name, category_l2_name, logged_by_line_user_id, tenant_type, tenant_id, metadata, periodic_schedule_id, created_at";

export async function requireExpenseUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    throw new Response("Unauthorized", { status: 401 });
  }
  return supabase;
}

function mapExpenseRow(row: Record<string, unknown>): ExpenseRecord {
  const description = String(row.description);
  return {
    id: String(row.id),
    expense_date: String(row.expense_date).slice(0, 10),
    description,
    amount: Number(row.amount),
    currency: String(row.currency),
    category_node_id: String(row.category_node_id),
    category_name_ja: row.category_name_ja ? String(row.category_name_ja) : null,
    category_l1_name: row.category_l1_name ? String(row.category_l1_name) : null,
    category_l2_name: row.category_l2_name ? String(row.category_l2_name) : null,
    logged_by_line_user_id: String(row.logged_by_line_user_id),
    tenant_type: String(row.tenant_type),
    tenant_id: String(row.tenant_id),
    merchant_display: resolveExpenseMerchantDisplay(row.metadata, description),
    periodic_schedule_id: row.periodic_schedule_id
      ? String(row.periodic_schedule_id)
      : null,
    created_at: String(row.created_at),
  };
}

export async function listExpenseFiscalMonths(
  tenantType: string,
  tenantId: string,
): Promise<FiscalMonthOption[]> {
  const supabase = await requireExpenseUser();
  await assertTenantAccess(supabase, tenantType, tenantId);

  const { data, error } = await supabase.rpc("list_expense_fiscal_months", {
    p_tenant_type: tenantType,
    p_tenant_id: tenantId,
  });

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  return ((data as FiscalMonthOption[] | null) ?? []).map((row) => ({
    budget_month: String(row.budget_month),
    expense_count: Number(row.expense_count),
    total_amount: Number(row.total_amount),
  }));
}

export type ListExpensesFilter = {
  categoryL1Id?: string;
  categoryL2Id?: string;
};

export async function listExpenses(
  tenantType: string,
  tenantId: string,
  budgetMonth: string,
  offset: number,
  limit: number,
  filter: ListExpensesFilter = {},
  sort: ExpenseListSort = DEFAULT_EXPENSE_LIST_SORT,
): Promise<ExpenseRecord[]> {
  const supabase = await requireExpenseUser();
  await assertTenantAccess(supabase, tenantType, tenantId);

  const periodEnd = fiscalPeriodEnd(budgetMonth);
  let query = supabase
    .from("v_expenses_enriched")
    .select(EXPENSE_SELECT)
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId)
    .eq("currency", "JPY")
    .is("deleted_at", null)
    .gte("expense_date", budgetMonth)
    .lte("expense_date", periodEnd);

  if (filter.categoryL2Id) {
    query = query.eq("category_l2_id", filter.categoryL2Id);
  } else if (filter.categoryL1Id) {
    query = query.eq("category_l1_id", filter.categoryL1Id);
  }

  const ascending = sort.dir === "asc";
  if (sort.field === "amount") {
    query = query
      .order("amount", { ascending })
      .order("created_at", { ascending })
      .order("id", { ascending });
  } else {
    // Newest/oldest: calendar date first, then log time within the same day.
    query = query
      .order("expense_date", { ascending })
      .order("created_at", { ascending })
      .order("id", { ascending });
  }

  const { data, error } = await query.range(offset, offset + limit - 1);

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  return (data ?? []).map((row) => mapExpenseRow(row as Record<string, unknown>));
}

export async function getExpenseById(id: string): Promise<ExpenseRecord> {
  const supabase = await requireExpenseUser();
  const { data, error } = await supabase
    .from("v_expenses_enriched")
    .select(EXPENSE_SELECT)
    .eq("id", id)
    .is("deleted_at", null)
    .maybeSingle();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }
  if (!data) {
    throw new Response("not_found", { status: 404 });
  }

  const row = mapExpenseRow(data as Record<string, unknown>);
  await assertTenantAccess(supabase, row.tenant_type, row.tenant_id);
  return row;
}

async function currentLineUserId(supabase: Awaited<ReturnType<typeof requireExpenseUser>>) {
  const { data, error } = await supabase.rpc("current_line_user_id");
  if (error || !data) {
    throw new Response("Unauthorized", { status: 401 });
  }
  return String(data);
}

export async function createExpense(
  payload: CreateExpensePayload,
): Promise<ExpenseRecord> {
  const supabase = await requireExpenseUser();
  await assertTenantAccess(supabase, payload.tenant_type, payload.tenant_id);

  const lineUserId = await currentLineUserId(supabase);
  const assignment = await resolveCategoryAssignment(
    payload.tenant_type,
    payload.tenant_id,
    payload.category_node_id,
  );

  const { data, error } = await supabase
    .from("expenses")
    .insert({
      tenant_type: payload.tenant_type,
      tenant_id: payload.tenant_id,
      line_user_id: lineUserId,
      logged_by_line_user_id: lineUserId,
      source_message_id: `web:${crypto.randomUUID()}`,
      line_item_index: 0,
      description: payload.description.trim() || "Expense",
      amount: payload.amount,
      currency: (payload.currency ?? "JPY").toUpperCase().slice(0, 3),
      expense_date: payload.expense_date.slice(0, 10),
      category_node_id: assignment.category_node_id,
      assigned_level: assignment.assigned_level,
      category_l1_id: assignment.category_l1_id,
      category_l2_id: assignment.category_l2_id,
      category_l3_id: null,
    })
    .select("id")
    .single();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  return getExpenseById(String(data.id));
}

export async function updateExpense(
  id: string,
  payload: UpdateExpensePayload,
): Promise<ExpenseRecord> {
  const supabase = await requireExpenseUser();
  const existing = await getExpenseById(id);
  const patch: Record<string, unknown> = {
    updated_at: new Date().toISOString(),
  };

  if (payload.description != null) {
    patch.description = payload.description.trim() || "Expense";
  }
  if (payload.amount != null) {
    patch.amount = payload.amount;
  }
  if (payload.expense_date != null) {
    patch.expense_date = payload.expense_date.slice(0, 10);
  }
  if (payload.currency != null) {
    patch.currency = payload.currency.toUpperCase().slice(0, 3);
  }
  if (payload.category_node_id) {
    const assignment = await resolveCategoryAssignment(
      existing.tenant_type,
      existing.tenant_id,
      payload.category_node_id,
    );
    patch.category_node_id = assignment.category_node_id;
    patch.assigned_level = assignment.assigned_level;
    patch.category_l1_id = assignment.category_l1_id;
    patch.category_l2_id = assignment.category_l2_id;
    patch.category_l3_id = null;
  }

  const { error } = await supabase
    .from("expenses")
    .update(patch)
    .eq("id", id)
    .is("deleted_at", null);

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  return getExpenseById(id);
}

export async function deleteExpense(id: string): Promise<void> {
  const supabase = await requireExpenseUser();
  await getExpenseById(id);
  const now = new Date().toISOString();
  const { error } = await supabase
    .from("expenses")
    .update({ deleted_at: now, updated_at: now })
    .eq("id", id)
    .is("deleted_at", null);

  if (error) {
    throw new Response(error.message, { status: 400 });
  }
}
