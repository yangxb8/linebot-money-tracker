import { NextResponse } from "next/server";
import {
  computeFirstRunDate,
  computeNextRunDate,
} from "@/lib/periodic/recurrence";
import type { RecurrenceRule } from "@/lib/periodic/types";
import { validateRecurrence } from "@/lib/periodic/validation";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const recurrenceCheck = validateRecurrence(body.recurrence);
    if (!recurrenceCheck.ok) {
      return NextResponse.json({ error: recurrenceCheck.error }, { status: 400 });
    }

    const recurrence = body.recurrence as RecurrenceRule;
    const startDate = String(body.start_date).slice(0, 10);
    const timezone = String(body.timezone ?? "Asia/Tokyo");
    const after = body.after
      ? String(body.after).slice(0, 10)
      : startDate;

    const nextRunDate = computeNextRunDate(recurrence, startDate, after);
    const followingRunDate = nextRunDate
      ? computeNextRunDate(recurrence, startDate, nextRunDate)
      : null;

    if (!nextRunDate && compareIso(after, startDate) < 0) {
      return NextResponse.json({
        next_run_date: computeFirstRunDate(recurrence, startDate, timezone),
        following_run_date: computeNextRunDate(
          recurrence,
          startDate,
          computeFirstRunDate(recurrence, startDate, timezone),
        ),
      });
    }

    return NextResponse.json({
      next_run_date: nextRunDate,
      following_run_date: followingRunDate,
    });
  } catch {
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}

function compareIso(a: string, b: string): number {
  return a.localeCompare(b);
}
