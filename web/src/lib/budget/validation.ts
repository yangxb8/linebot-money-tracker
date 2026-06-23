import type {
  BudgetClearItem,
  BudgetUpsertItem,
  PutBudgetPayload,
} from "@/lib/budget/types";

export function validatePutBudgetPayload(body: unknown): PutBudgetPayload {
  if (!body || typeof body !== "object") {
    throw new Error("invalid_body");
  }
  const raw = body as Record<string, unknown>;
  const tenant_type = String(raw.tenant_type ?? "");
  const tenant_id = String(raw.tenant_id ?? "");
  const budget_month = String(raw.budget_month ?? "");
  const currency = String(raw.currency ?? "JPY");

  if (!tenant_type || !tenant_id || !budget_month) {
    throw new Error("missing_fields");
  }
  if (currency !== "JPY") {
    throw new Error("unsupported_currency");
  }

  const budgets = validateUpsertItems(raw.budgets);
  const clear_levels = validateClearItems(raw.clear_levels);

  return {
    tenant_type,
    tenant_id,
    budget_month,
    currency,
    budgets,
    clear_levels,
  };
}

function validateUpsertItems(value: unknown): BudgetUpsertItem[] {
  if (value == null) return [];
  if (!Array.isArray(value)) throw new Error("invalid_budgets");

  return value.map((item) => {
    if (!item || typeof item !== "object") throw new Error("invalid_budget_item");
    const row = item as Record<string, unknown>;
    const budget_level = String(row.budget_level ?? "") as BudgetUpsertItem["budget_level"];
    if (budget_level !== "total" && budget_level !== "l1" && budget_level !== "l2") {
      throw new Error("invalid_budget_level");
    }
    const amount = Number(row.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      throw new Error("invalid_amount");
    }
    const category_node_id =
      row.category_node_id == null ? null : String(row.category_node_id);
    if (budget_level === "total" && category_node_id) {
      throw new Error("total_must_not_have_category");
    }
    if (budget_level !== "total" && !category_node_id) {
      throw new Error("category_required");
    }
    return { budget_level, category_node_id, amount: Math.round(amount) };
  });
}

function validateClearItems(value: unknown): BudgetClearItem[] {
  if (value == null) return [];
  if (!Array.isArray(value)) throw new Error("invalid_clear_levels");

  return value.map((item) => {
    if (!item || typeof item !== "object") throw new Error("invalid_clear_item");
    const row = item as Record<string, unknown>;
    const budget_level = String(row.budget_level ?? "") as BudgetClearItem["budget_level"];
    if (budget_level !== "total" && budget_level !== "l1" && budget_level !== "l2") {
      throw new Error("invalid_budget_level");
    }
    const category_node_id =
      row.category_node_id == null ? null : String(row.category_node_id);
    if (budget_level === "total" && category_node_id) {
      throw new Error("total_must_not_have_category");
    }
    if (budget_level !== "total" && !category_node_id) {
      throw new Error("category_required");
    }
    return { budget_level, category_node_id };
  });
}
