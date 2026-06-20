import { NextResponse } from "next/server";
import {
  exchangeCodeForTokens,
  validateOAuthState,
} from "@/lib/line/oauth";
import { linkLineUserAndCreateSession } from "@/lib/line/session";
import { verifyLineIdToken } from "@/lib/line/verify-id-token";

function authFailedRedirect(request: Request) {
  const url = new URL("/login", request.url);
  url.searchParams.set("error", "auth_failed");
  return NextResponse.redirect(url);
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");

  if (!code) {
    console.error("[auth/line/callback] missing authorization code");
    return authFailedRedirect(request);
  }

  const stateValid = await validateOAuthState(state);
  if (!stateValid) {
    console.error("[auth/line/callback] invalid OAuth state");
    return authFailedRedirect(request);
  }

  try {
    const tokens = await exchangeCodeForTokens(code);
    const profile = await verifyLineIdToken(tokens.id_token);
    await linkLineUserAndCreateSession(profile);
    console.info("[auth/line/callback] session created", {
      provider: "line_oauth",
    });
    return NextResponse.redirect(new URL("/dashboard", request.url));
  } catch (error) {
    console.error("[auth/line/callback] auth failed", {
      reason: error instanceof Error ? error.message : "unknown",
    });
    return authFailedRedirect(request);
  }
}
