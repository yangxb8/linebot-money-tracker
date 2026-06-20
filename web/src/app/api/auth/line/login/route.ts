import { NextResponse } from "next/server";
import { buildLineAuthorizeUrl, createOAuthState } from "@/lib/line/oauth";

export async function GET() {
  const state = await createOAuthState();
  return NextResponse.redirect(buildLineAuthorizeUrl(state));
}
