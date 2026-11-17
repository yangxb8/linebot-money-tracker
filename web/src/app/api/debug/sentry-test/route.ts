import { NextResponse } from "next/server";

/**
 * Throws a deliberate error so we can verify Sentry capture.
 * Only enabled when ALLOW_SENTRY_TEST=1.
 */
export async function GET() {
  if (process.env.ALLOW_SENTRY_TEST !== "1") {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  throw new Error("Sentry Test Error");
}
