import { NextResponse } from "next/server";
import {
  currentBudgetMonthJst,
  isCurrentBudgetMonth,
} from "@/lib/budget/format";
import {
  fetchBudgetSummary,
  parseTenantParams,
  upsertBudgetRows,
} from "@/lib/budget/server";
import { validatePutBudgetPayload } from "@/lib/budget/validation";
import { fetchTenantSettings } from "@/lib/settings/server";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const { tenantType, tenantId } = parseTenantParams(
      url.searchParams.get("tenant_type"),
      url.searchParams.get("tenant_id"),
    );
    const settings = await fetchTenantSettings(tenantType, tenantId);
    const budgetMonth =
      url.searchParams.get("budget_month") ??
      currentBudgetMonthJst(settings.fiscal_start_day);

    const summary = await fetchBudgetSummary(
      tenantType,
      tenantId,
      budgetMonth,
    );
    return NextResponse.json(summary);
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

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const payload = validatePutBudgetPayload(body);
    const settings = await fetchTenantSettings(
      payload.tenant_type,
      payload.tenant_id,
    );

    if (!isCurrentBudgetMonth(payload.budget_month, settings.fiscal_start_day)) {
      return NextResponse.json(
        { error: "only_current_month_editable" },
        { status: 400 },
      );
    }

    await upsertBudgetRows(
      payload.tenant_type,
      payload.tenant_id,
      payload.budget_month,
      payload.currency ?? "JPY",
      (payload.budgets ?? []).map((b) => ({
        budget_level: b.budget_level,
        category_node_id:
          b.budget_level === "total" ? null : (b.category_node_id ?? null),
        amount: b.amount,
      })),
      (payload.clear_levels ?? []).map((c) => ({
        budget_level: c.budget_level,
        category_node_id:
          c.budget_level === "total" ? null : (c.category_node_id ?? null),
      })),
    );

    const summary = await fetchBudgetSummary(
      payload.tenant_type,
      payload.tenant_id,
      payload.budget_month,
    );
    return NextResponse.json(summary);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("invalid")) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    if (error instanceof Response) {
      return NextResponse.json(
        { error: await error.text() },
        { status: error.status },
      );
    }
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
