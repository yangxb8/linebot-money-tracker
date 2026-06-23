import { NextResponse } from "next/server";
import { shiftBudgetMonth } from "@/lib/budget/format";
import { parseTenantParams, requireBudgetUser } from "@/lib/budget/server";
import { assertTenantAccess } from "@/lib/periodic/tenant-access";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const tenantType = String(body.tenant_type ?? "");
    const tenantId = String(body.tenant_id ?? "");
    const targetMonth = String(body.target_month ?? "");
    parseTenantParams(tenantType, tenantId);

    if (!targetMonth) {
      return NextResponse.json({ error: "target_month required" }, { status: 400 });
    }

    const supabase = await requireBudgetUser();
    await assertTenantAccess(supabase, tenantType, tenantId);

    const sourceMonth = shiftBudgetMonth(targetMonth, -1);

    const { data, error } = await supabase
      .from("monthly_budgets")
      .select("budget_level, category_node_id, amount")
      .eq("tenant_type", tenantType)
      .eq("tenant_id", tenantId)
      .eq("budget_month", sourceMonth)
      .eq("currency", "JPY");

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    const rows = data ?? [];
    if (rows.length === 0) {
      return NextResponse.json({ available: false, source_month: sourceMonth, budgets: [] });
    }

    return NextResponse.json({
      available: true,
      source_month: sourceMonth,
      budgets: rows.map((r) => ({
        budget_level: r.budget_level,
        category_node_id: r.category_node_id,
        amount: Number(r.amount),
      })),
    });
  } catch (error) {
    if (error instanceof Response) {
      return NextResponse.json(
        { error: await error.text() },
        { status: error.status },
      );
    }
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
