import { NextResponse } from "next/server";
import { PAGE_SIZE } from "@/lib/dashboard/format";
import {
  createExpense,
  listExpenses,
  parseTenantParams,
} from "@/lib/expenses/server";
import { parseExpenseListSort } from "@/lib/expenses/sort-group";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const { tenantType, tenantId } = parseTenantParams(
      url.searchParams.get("tenant_type"),
      url.searchParams.get("tenant_id"),
    );
    const budgetMonth = url.searchParams.get("budget_month");
    if (!budgetMonth) {
      return NextResponse.json({ error: "budget_month required" }, { status: 400 });
    }

    const offset = Math.max(0, Number(url.searchParams.get("offset") ?? 0));
    const limit = Math.min(
      200,
      Math.max(1, Number(url.searchParams.get("limit") ?? PAGE_SIZE)),
    );
    const categoryL1Id = url.searchParams.get("category_l1_id") || undefined;
    const categoryL2Id = url.searchParams.get("category_l2_id") || undefined;
    const sort = parseExpenseListSort(
      url.searchParams.get("sort_field"),
      url.searchParams.get("sort_dir"),
    );

    const rows = await listExpenses(
      tenantType,
      tenantId,
      budgetMonth,
      offset,
      limit,
      { categoryL1Id, categoryL2Id },
      sort,
    );
    return NextResponse.json(rows);
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

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const tenantType = String(body.tenant_type ?? "");
    const tenantId = String(body.tenant_id ?? "");
    parseTenantParams(tenantType, tenantId);

    const description = String(body.description ?? "").trim();
    const amount = Number(body.amount);
    const expenseDate = String(body.expense_date ?? "").slice(0, 10);
    const categoryNodeId = String(body.category_node_id ?? "");

    if (!description) {
      return NextResponse.json({ error: "description_required" }, { status: 400 });
    }
    if (!Number.isFinite(amount) || amount <= 0) {
      return NextResponse.json({ error: "invalid_amount" }, { status: 400 });
    }
    if (!expenseDate) {
      return NextResponse.json({ error: "expense_date_required" }, { status: 400 });
    }
    if (!categoryNodeId) {
      return NextResponse.json({ error: "category_required" }, { status: 400 });
    }

    const expense = await createExpense({
      tenant_type: tenantType,
      tenant_id: tenantId,
      description,
      amount,
      expense_date: expenseDate,
      category_node_id: categoryNodeId,
      currency: body.currency ? String(body.currency) : "JPY",
    });
    return NextResponse.json(expense, { status: 201 });
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
