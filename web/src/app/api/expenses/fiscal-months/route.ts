import { NextResponse } from "next/server";
import {
  listExpenseFiscalMonths,
  parseTenantParams,
} from "@/lib/expenses/server";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const { tenantType, tenantId } = parseTenantParams(
      url.searchParams.get("tenant_type"),
      url.searchParams.get("tenant_id"),
    );
    const months = await listExpenseFiscalMonths(tenantType, tenantId);
    return NextResponse.json(months);
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
