export const PAGE_SIZE = Number(process.env.EXPENSE_PAGE_SIZE ?? 20);

export type ExpenseRow = {
  id: string;
  expense_date: string;
  description: string;
  amount: number;
  currency: string;
  category_name_ja: string | null;
  category_l1_name: string | null;
  category_l2_name: string | null;
  logged_by_line_user_id: string;
  tenant_type: string;
  tenant_id: string;
};

export function categoryLabel(row: ExpenseRow): string {
  if (row.category_l2_name) {
    const l1 = row.category_l1_name ?? "";
    return l1 ? `${l1} › ${row.category_l2_name}` : row.category_l2_name;
  }
  return row.category_l1_name ?? row.category_name_ja ?? "—";
}
