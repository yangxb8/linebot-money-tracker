import { NextResponse } from "next/server";
import { buildLineAuthorizeUrl, createOAuthState } from "@/lib/line/oauth";

export async function GET() {
  const state = createOAuthState();
  return NextResponse.redirect(buildLineAuthorizeUrl(state));
}
