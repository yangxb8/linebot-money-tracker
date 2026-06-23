import type { BudgetSummary, PutBudgetPayload, SuggestionRow } from "@/lib/budget/types";
import type { TenantOption } from "@/lib/dashboard/tenants";

function tenantQuery(tenant: TenantOption): string {
  return `tenant_type=${encodeURIComponent(tenant.tenantType)}&tenant_id=${encodeURIComponent(tenant.tenantId)}`;
}

export async function fetchBudgetSummary(
  tenant: TenantOption,
  budgetMonth?: string,
): Promise<BudgetSummary> {
  const monthParam = budgetMonth
    ? `&budget_month=${encodeURIComponent(budgetMonth)}`
    : "";
  const res = await fetch(`/api/budgets?${tenantQuery(tenant)}${monthParam}`);
  if (!res.ok) {
    throw new Error("fetch_failed");
  }
  return res.json() as Promise<BudgetSummary>;
}

export async function saveBudgets(payload: PutBudgetPayload): Promise<BudgetSummary> {
  const res = await fetch("/api/budgets", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error("save_failed");
  }
  return res.json() as Promise<BudgetSummary>;
}

export async function copyBudgetsFromPrevious(
  tenant: TenantOption,
  targetMonth: string,
): Promise<{ available: boolean; budgets: PutBudgetPayload["budgets"] }> {
  const res = await fetch("/api/budgets/copy-from-previous", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_type: tenant.tenantType,
      tenant_id: tenant.tenantId,
      target_month: targetMonth,
    }),
  });
  if (!res.ok) throw new Error("copy_failed");
  return res.json() as Promise<{
    available: boolean;
    budgets: PutBudgetPayload["budgets"];
  }>;
}

export async function fetchBudgetSuggestions(
  tenant: TenantOption,
  budgetMonth?: string,
  categoryNodeId?: string,
): Promise<SuggestionRow[]> {
  const params = new URLSearchParams({
    tenant_type: tenant.tenantType,
    tenant_id: tenant.tenantId,
  });
  if (budgetMonth) params.set("budget_month", budgetMonth);
  if (categoryNodeId) params.set("category_node_id", categoryNodeId);
  const res = await fetch(`/api/budgets/suggestions?${params.toString()}`);
  if (!res.ok) throw new Error("suggestions_failed");
  const data = (await res.json()) as { suggestions: SuggestionRow[] };
  return data.suggestions;
}
