import { NextResponse } from "next/server";
import { linkLineUserAndCreateSession } from "@/lib/line/session";
import { verifyLineIdToken } from "@/lib/line/verify-id-token";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const idToken = body?.idToken;
    if (!idToken || typeof idToken !== "string") {
      return NextResponse.json({ ok: false }, { status: 400 });
    }

    const profile = await verifyLineIdToken(idToken);
    await linkLineUserAndCreateSession(profile);
    console.info("[auth/line/liff] session created", { provider: "line_liff" });
    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("[auth/line/liff] auth failed", {
      reason: error instanceof Error ? error.message : "unknown",
    });
    return NextResponse.json({ ok: false }, { status: 401 });
  }
}
