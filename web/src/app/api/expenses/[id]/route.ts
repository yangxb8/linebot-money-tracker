import { NextResponse } from "next/server";
import {
  deleteExpense,
  getExpenseById,
  updateExpense,
} from "@/lib/expenses/server";

type RouteParams = { params: Promise<{ id: string }> };

export async function GET(_request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    const expense = await getExpenseById(id);
    return NextResponse.json(expense);
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

export async function PATCH(request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    const body = await request.json();
    const patch: {
      description?: string;
      amount?: number;
      expense_date?: string;
      category_node_id?: string;
      currency?: string;
    } = {};

    if (body.description != null) {
      const description = String(body.description).trim();
      if (!description) {
        return NextResponse.json({ error: "description_required" }, { status: 400 });
      }
      patch.description = description;
    }
    if (body.amount != null) {
      const amount = Number(body.amount);
      if (!Number.isFinite(amount) || amount <= 0) {
        return NextResponse.json({ error: "invalid_amount" }, { status: 400 });
      }
      patch.amount = amount;
    }
    if (body.expense_date != null) {
      patch.expense_date = String(body.expense_date).slice(0, 10);
    }
    if (body.category_node_id != null) {
      patch.category_node_id = String(body.category_node_id);
    }
    if (body.currency != null) {
      patch.currency = String(body.currency);
    }

    const expense = await updateExpense(id, patch);
    return NextResponse.json(expense);
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

export async function DELETE(_request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    await deleteExpense(id);
    return new NextResponse(null, { status: 204 });
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
