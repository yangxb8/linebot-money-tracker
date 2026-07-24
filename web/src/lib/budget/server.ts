import { createClient } from "@/lib/supabase/server";
import {
  assertTenantAccess,
  parseTenantParams,
} from "@/lib/periodic/tenant-access";
import type {
  BudgetCategoryNode,
  BudgetMeter,
  BudgetSummary,
  RpcBudgetSummary,
} from "@/lib/budget/types";
import { currentBudgetMonthJst, fiscalPeriodEnd } from "@/lib/budget/format";

export { parseTenantParams, assertTenantAccess };

export async function requireBudgetUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    throw new Response("Unauthorized", { status: 401 });
  }
  return supabase;
}

type DbCategory = {
  id: string;
  code: string;
  name_ja: string;
  level: number;
  parent_id: string | null;
  sort_order: number;
};

export type CategorySpentTotals = {
  byL1: Record<string, number>;
  byL2: Record<string, number>;
};

export function buildCategorySpentTotals(
  expenses: {
    assigned_level: number;
    category_node_id: string;
    category_l1_id: string;
    amount: number | string;
  }[],
): CategorySpentTotals {
  const byL1: Record<string, number> = {};
  const byL2: Record<string, number> = {};
  for (const expense of expenses) {
    const amount = Number(expense.amount);
    byL1[expense.category_l1_id] = (byL1[expense.category_l1_id] ?? 0) + amount;
    if (expense.assigned_level === 2) {
      byL2[expense.category_node_id] =
        (byL2[expense.category_node_id] ?? 0) + amount;
    }
  }
  return { byL1, byL2 };
}

function buildMeter(limit: number | null, spent: number): BudgetMeter {
  const has_limit = limit != null && limit > 0;
  const remaining = has_limit ? Math.max(limit - spent, 0) : null;
  const spent_pct = has_limit && limit > 0 ? spent / limit : null;
  return { limit, spent, remaining, spent_pct, has_limit };
}

export function enrichBudgetSummary(
  rpc: RpcBudgetSummary,
  nodes: DbCategory[],
  categorySpent?: CategorySpentTotals,
): BudgetSummary {
  const limitFor = (level: string, nodeId: string | null): number | null => {
    const row = rpc.budgets.find(
      (b) =>
        b.budget_level === level &&
        (level === "total"
          ? b.category_node_id == null
          : b.category_node_id === nodeId),
    );
    return row?.amount ?? null;
  };

  const spentAssigned = (level: "l1" | "l2", nodeId: string): number =>
    rpc.spent_by_bucket[`${level}:${nodeId}`] ?? 0;

  const l1Nodes = nodes
    .filter((n) => n.level === 1)
    .slice()
    .sort((a, b) => {
      if (a.code === "unknown" && b.code !== "unknown") return 1;
      if (b.code === "unknown" && a.code !== "unknown") return -1;
      return a.sort_order - b.sort_order;
    });
  const categories: BudgetCategoryNode[] = l1Nodes.map((l1) => {
    const children = nodes
      .filter((n) => n.parent_id === l1.id && n.level === 2)
      .map((l2) => {
        const limit = limitFor("l2", l2.id);
        const assigned = spentAssigned("l2", l2.id);
        const spentAggregate = categorySpent?.byL2[l2.id] ?? assigned;
        return {
          node_id: l2.id,
          code: l2.code,
          name_ja: l2.name_ja,
          level: 2 as const,
          limit,
          spent: spentAggregate,
          spent_assigned: assigned,
          spent_aggregate: spentAggregate,
          suggested_from_children: null,
          has_limit: limit != null,
        };
      });

    const childLimitSum = children.reduce((s, c) => s + (c.limit ?? 0), 0);
    const l1Limit = limitFor("l1", l1.id);
    const l1Assigned = spentAssigned("l1", l1.id);
    const l1Aggregate =
      categorySpent?.byL1[l1.id] ??
      children.reduce((s, c) => s + c.spent_aggregate, 0) + l1Assigned;

    return {
      node_id: l1.id,
      code: l1.code,
      name_ja: l1.name_ja,
      level: 1 as const,
      limit: l1Limit,
      spent: l1Aggregate,
      spent_assigned: l1Assigned,
      spent_aggregate: l1Aggregate,
      suggested_from_children: childLimitSum > 0 ? childLimitSum : null,
      has_limit: l1Limit != null,
      children,
    };
  });

  const totalLimit = limitFor("total", null);

  return {
    budget_month: rpc.budget_month,
    fiscal_period_end: rpc.fiscal_period_end,
    fiscal_start_day: rpc.fiscal_start_day,
    days_in_month: rpc.days_in_month,
    elapsed_days: rpc.elapsed_days,
    currency: rpc.currency,
    total: buildMeter(totalLimit, rpc.total_spent_all),
    categories,
    unbudgeted_spent: rpc.unbudgeted_spent,
    has_any_limit: rpc.has_any_limit,
    lazy_copied_from_previous: Boolean(rpc.lazy_copied_from_previous),
  };
}

export async function fetchBudgetSummary(
  tenantType: string,
  tenantId: string,
  budgetMonth?: string,
): Promise<BudgetSummary> {
  const supabase = await requireBudgetUser();
  await assertTenantAccess(supabase, tenantType, tenantId);

  const month = budgetMonth ?? currentBudgetMonthJst();

  const { data: rpcData, error: rpcError } = await supabase.rpc(
    "get_budget_summary",
    {
      p_tenant_type: tenantType,
      p_tenant_id: tenantId,
      p_budget_month: month,
      p_currency: "JPY",
    },
  );

  if (rpcError) {
    throw new Response(rpcError.message, { status: 400 });
  }

  const rpc = rpcData as RpcBudgetSummary;

  const { data: nodes, error: nodeError } = await supabase
    .from("category_nodes")
    .select("id, code, name_ja, level, parent_id, sort_order")
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId)
    .order("level")
    .order("sort_order");

  if (nodeError) {
    throw new Response(nodeError.message, { status: 400 });
  }

  const periodEnd = fiscalPeriodEnd(month);
  const { data: expenseRows, error: expenseError } = await supabase
    .from("expenses")
    .select("assigned_level, category_node_id, category_l1_id, amount")
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId)
    .eq("currency", "JPY")
    .is("deleted_at", null)
    .gte("expense_date", month)
    .lte("expense_date", periodEnd);

  if (expenseError) {
    throw new Response(expenseError.message, { status: 400 });
  }

  const categorySpent = buildCategorySpentTotals(expenseRows ?? []);

  return enrichBudgetSummary(rpc, (nodes ?? []) as DbCategory[], categorySpent);
}

export async function upsertBudgetRows(
  tenantType: string,
  tenantId: string,
  budgetMonth: string,
  currency: string,
  budgets: {
    budget_level: string;
    category_node_id: string | null;
    amount: number;
  }[],
  clearLevels: { budget_level: string; category_node_id: string | null }[],
): Promise<void> {
  const supabase = await requireBudgetUser();
  await assertTenantAccess(supabase, tenantType, tenantId);

  for (const item of clearLevels) {
    let q = supabase
      .from("monthly_budgets")
      .delete()
      .eq("tenant_type", tenantType)
      .eq("tenant_id", tenantId)
      .eq("budget_month", budgetMonth)
      .eq("currency", currency)
      .eq("budget_level", item.budget_level);

    if (item.budget_level === "total") {
      q = q.is("category_node_id", null);
    } else {
      q = q.eq("category_node_id", item.category_node_id!);
    }

    const { error } = await q;
    if (error) throw new Response(error.message, { status: 400 });
  }

  for (const item of budgets) {
    let existingQuery = supabase
      .from("monthly_budgets")
      .select("id")
      .eq("tenant_type", tenantType)
      .eq("tenant_id", tenantId)
      .eq("budget_month", budgetMonth)
      .eq("currency", currency)
      .eq("budget_level", item.budget_level);

    if (item.budget_level === "total") {
      existingQuery = existingQuery.is("category_node_id", null);
    } else {
      existingQuery = existingQuery.eq(
        "category_node_id",
        item.category_node_id!,
      );
    }

    const { data: existing } = await existingQuery.maybeSingle();

    if (existing?.id) {
      const { error } = await supabase
        .from("monthly_budgets")
        .update({
          amount: item.amount,
          updated_at: new Date().toISOString(),
        })
        .eq("id", existing.id);
      if (error) throw new Response(error.message, { status: 400 });
    } else {
      const { error } = await supabase.from("monthly_budgets").insert({
        tenant_type: tenantType,
        tenant_id: tenantId,
        budget_month: budgetMonth,
        currency,
        budget_level: item.budget_level,
        category_node_id: item.category_node_id,
        amount: item.amount,
      });
      if (error) throw new Response(error.message, { status: 400 });
    }
  }
}
