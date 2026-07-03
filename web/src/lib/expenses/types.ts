export type ExpenseRecord = {
  id: string;
  expense_date: string;
  description: string;
  amount: number;
  currency: string;
  category_node_id: string;
  category_name_ja: string | null;
  category_l1_name: string | null;
  category_l2_name: string | null;
  logged_by_line_user_id: string;
  tenant_type: string;
  tenant_id: string;
  merchant_display: string | null;
};

export type FiscalMonthOption = {
  budget_month: string;
  expense_count: number;
  total_amount: number;
};

export type ExpenseFormValues = {
  description: string;
  amount: string;
  expense_date: string;
  category_node_id: string;
};

export type CreateExpensePayload = {
  tenant_type: string;
  tenant_id: string;
  description: string;
  amount: number;
  expense_date: string;
  category_node_id: string;
  currency?: string;
};

export type UpdateExpensePayload = {
  description?: string;
  amount?: number;
  expense_date?: string;
  category_node_id?: string;
  currency?: string;
};
