import type { TenantOption } from "@/lib/dashboard/tenants";
import type { ExpenseListSort } from "@/lib/expenses/sort-group";
import type {
  CreateExpensePayload,
  ExpenseRecord,
  FiscalMonthOption,
  UpdateExpensePayload,
} from "@/lib/expenses/types";

function tenantQuery(tenant: TenantOption): string {
  return `tenant_type=${encodeURIComponent(tenant.tenantType)}&tenant_id=${encodeURIComponent(tenant.tenantId)}`;
}

export async function fetchExpenseFiscalMonths(
  tenant: TenantOption,
): Promise<FiscalMonthOption[]> {
  const response = await fetch(`/api/expenses/fiscal-months?${tenantQuery(tenant)}`);
  if (!response.ok) {
    throw new Error("Failed to load fiscal months");
  }
  return response.json() as Promise<FiscalMonthOption[]>;
}

export type ExpenseCategoryFilter = {
  categoryL1Id?: string;
  categoryL2Id?: string;
};

export async function fetchExpensesForMonth(
  tenant: TenantOption,
  budgetMonth: string,
  offset: number,
  limit?: number,
  filter: ExpenseCategoryFilter = {},
  sort?: ExpenseListSort,
): Promise<ExpenseRecord[]> {
  const params = new URLSearchParams({
    tenant_type: tenant.tenantType,
    tenant_id: tenant.tenantId,
    budget_month: budgetMonth,
    offset: String(offset),
  });
  if (limit !== undefined) {
    params.set("limit", String(limit));
  }
  if (sort) {
    params.set("sort_field", sort.field);
    params.set("sort_dir", sort.dir);
  }
  if (filter.categoryL2Id) {
    params.set("category_l2_id", filter.categoryL2Id);
  } else if (filter.categoryL1Id) {
    params.set("category_l1_id", filter.categoryL1Id);
  }
  const response = await fetch(`/api/expenses?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Failed to load expenses");
  }
  return response.json() as Promise<ExpenseRecord[]>;
}

export async function fetchAllExpensesForMonth(
  tenant: TenantOption,
  budgetMonth: string,
  pageSize: number,
): Promise<ExpenseRecord[]> {
  const all: ExpenseRecord[] = [];
  let offset = 0;
  while (true) {
    const page = await fetchExpensesForMonth(tenant, budgetMonth, offset, pageSize);
    all.push(...page);
    if (page.length < pageSize) break;
    offset += page.length;
  }
  return all;
}

export async function createExpense(
  payload: CreateExpensePayload,
): Promise<ExpenseRecord> {
  const response = await fetch("/api/expenses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(data.error ?? "Failed to create expense");
  }
  return response.json() as Promise<ExpenseRecord>;
}

export async function updateExpense(
  id: string,
  payload: UpdateExpensePayload,
): Promise<ExpenseRecord> {
  const response = await fetch(`/api/expenses/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(data.error ?? "Failed to update expense");
  }
  return response.json() as Promise<ExpenseRecord>;
}

export async function deleteExpense(id: string): Promise<void> {
  const response = await fetch(`/api/expenses/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(data.error ?? "Failed to delete expense");
  }
}

export function expenseToFormValues(expense: ExpenseRecord) {
  return {
    description: expense.description,
    amount: String(expense.amount),
    expense_date: expense.expense_date,
    category_node_id: expense.category_node_id,
  };
}

export function defaultExpenseFormValues(expenseDate: string) {
  return {
    description: "",
    amount: "",
    expense_date: expenseDate,
    category_node_id: "",
  };
}
