import { createClient } from "@/lib/supabase/client";
import { PAGE_SIZE, type ExpenseRow } from "@/lib/dashboard/format";

export async function fetchExpenses(
  tenantType: string,
  tenantId: string,
  offset: number,
): Promise<{ rows: ExpenseRow[]; error: string | null }> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("v_expenses_enriched")
    .select(
      "id, expense_date, description, amount, currency, category_name_ja, category_l1_name, category_l2_name, logged_by_line_user_id, tenant_type, tenant_id",
    )
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId)
    .eq("currency", "JPY")
    .is("deleted_at", null)
    .order("expense_date", { ascending: false })
    .order("created_at", { ascending: false })
    .range(offset, offset + PAGE_SIZE - 1);

  if (error) {
    return { rows: [], error: error.message };
  }

  return { rows: (data ?? []) as ExpenseRow[], error: null };
}
