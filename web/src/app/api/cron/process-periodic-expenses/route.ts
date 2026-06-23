import { NextResponse } from "next/server";
import { runPeriodicCron } from "@/lib/periodic/cron";

export async function GET(request: Request) {
  const authHeader = request.headers.get("authorization");
  const secret = process.env.CRON_SECRET;
  if (!secret || authHeader !== `Bearer ${secret}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const result = await runPeriodicCron();
    console.info(
      "[cron:periodic-expenses] processed=%d inserted=%d skipped=%d ended=%d",
      result.processed,
      result.inserted,
      result.skipped,
      result.ended,
    );
    return NextResponse.json(result);
  } catch (error) {
    console.error("[cron:periodic-expenses] failed", error);
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
