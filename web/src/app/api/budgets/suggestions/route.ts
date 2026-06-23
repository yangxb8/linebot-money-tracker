import { NextResponse } from "next/server";
import { parseTenantParams, requireBudgetUser } from "@/lib/budget/server";
import { currentBudgetMonthJst } from "@/lib/budget/format";
import { assertTenantAccess } from "@/lib/periodic/tenant-access";

function priorMonth(year: number, month: number, offset: number): { year: number; month: number } {
  const d = new Date(Date.UTC(year, month - 1 - offset, 1));
  return { year: d.getUTCFullYear(), month: d.getUTCMonth() + 1 };
}

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const { tenantType, tenantId } = parseTenantParams(
      url.searchParams.get("tenant_type"),
      url.searchParams.get("tenant_id"),
    );
    const budgetMonth =
      url.searchParams.get("budget_month") ?? currentBudgetMonthJst();
    const categoryNodeId = url.searchParams.get("category_node_id");

    const supabase = await requireBudgetUser();
    await assertTenantAccess(supabase, tenantType, tenantId);

    let nodeQuery = supabase
      .from("category_nodes")
      .select("id, level")
      .eq("tenant_type", tenantType)
      .eq("tenant_id", tenantId);

    if (categoryNodeId) {
      nodeQuery = nodeQuery.eq("id", categoryNodeId);
    }

    const { data: nodes, error: nodeError } = await nodeQuery;
    if (nodeError) {
      return NextResponse.json({ error: nodeError.message }, { status: 400 });
    }

    const [y, m] = budgetMonth.split("-").map(Number);
    const suggestions = [];

    for (const node of nodes ?? []) {
      let total = 0;
      let sampled = 0;
      for (let i = 1; i <= 3; i += 1) {
        const { year, month } = priorMonth(y, m, i);
        const { data: amount, error } = await supabase.rpc("monthly_expense_total", {
          p_tenant_type: tenantType,
          p_tenant_id: tenantId,
          p_year: year,
          p_month: month,
          p_category_node_id: node.id,
          p_currency: "JPY",
        });
        if (error) continue;
        const val = Number(amount ?? 0);
        if (val > 0) {
          total += val;
          sampled += 1;
        }
      }
      suggestions.push({
        category_node_id: node.id,
        level: node.level as 1 | 2,
        average_monthly_spent: sampled > 0 ? Math.round(total / sampled) : 0,
        months_sampled: sampled,
      });
    }

    return NextResponse.json({ suggestions });
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
