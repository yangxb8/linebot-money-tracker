export type BudgetLevel = "total" | "l1" | "l2";

export type BudgetBucket =
  | { kind: "total" }
  | { kind: "l1"; categoryNodeId: string }
  | { kind: "l2"; categoryNodeId: string }
  | { kind: "unbudgeted" };

export type BudgetLimitRow = {
  budget_level: BudgetLevel;
  category_node_id: string | null;
  amount: number;
};

export type BudgetMeter = {
  limit: number | null;
  spent: number;
  remaining: number | null;
  spent_pct: number | null;
  has_limit: boolean;
};

export type BudgetCategoryNode = {
  node_id: string;
  code: string;
  name_ja: string;
  level: 1 | 2;
  limit: number | null;
  spent: number;
  spent_assigned: number;
  spent_aggregate: number;
  suggested_from_children: number | null;
  has_limit: boolean;
  orphan?: boolean;
  children?: BudgetCategoryNode[];
};

export type BudgetSummary = {
  budget_month: string;
  fiscal_period_end?: string;
  fiscal_start_day?: number;
  days_in_month: number;
  elapsed_days: number;
  currency: string;
  total: BudgetMeter;
  categories: BudgetCategoryNode[];
  unbudgeted_spent: number;
  has_any_limit: boolean;
  lazy_copied_from_previous?: boolean;
};

export type HealthTone = "neutral" | "good" | "caution" | "bad";

export type HealthResult = {
  spentPct: number | null;
  timePct: number;
  paceRatio: number | null;
  tone: HealthTone;
  labelKey:
    | "budgetPaceNeutral"
    | "budgetPaceOnTrack"
    | "budgetPaceCaution"
    | "budgetPaceOver";
};

export type BudgetUpsertItem = {
  budget_level: BudgetLevel;
  category_node_id?: string | null;
  amount: number;
};

export type BudgetClearItem = {
  budget_level: BudgetLevel;
  category_node_id?: string | null;
};

export type PutBudgetPayload = {
  tenant_type: string;
  tenant_id: string;
  budget_month: string;
  currency?: string;
  budgets?: BudgetUpsertItem[];
  clear_levels?: BudgetClearItem[];
};

export type RpcBudgetSummary = {
  budget_month: string;
  fiscal_period_end?: string;
  fiscal_start_day?: number;
  days_in_month: number;
  elapsed_days: number;
  currency: string;
  total_limit: number | null;
  total_spent_all: number;
  unbudgeted_spent: number;
  has_any_limit: boolean;
  lazy_copied_from_previous?: boolean;
  budgets: BudgetLimitRow[];
  spent_by_bucket: Record<string, number>;
};

export type SuggestionRow = {
  category_node_id: string;
  level: 1 | 2;
  average_monthly_spent: number;
  months_sampled: number;
};
