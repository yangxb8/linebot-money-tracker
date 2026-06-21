import { NextResponse } from "next/server";
import {
  exchangeCodeForTokens,
  validateOAuthState,
} from "@/lib/line/oauth";
import { linkLineUserAndCreateSession } from "@/lib/line/session";
import { verifyLineIdToken } from "@/lib/line/verify-id-token";

function loginErrorRedirect(
  request: Request,
  error: string,
  reason?: string,
) {
  const url = new URL("/login", request.url);
  url.searchParams.set("error", error);
  if (reason) {
    url.searchParams.set("reason", reason.slice(0, 200));
  }
  return NextResponse.redirect(url);
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const lineError = url.searchParams.get("error");
  const lineErrorDescription = url.searchParams.get("error_description");

  if (lineError) {
    console.error("[auth/line/callback] LINE OAuth error", {
      error: lineError,
      description: lineErrorDescription,
    });
    return loginErrorRedirect(
      request,
      "line_oauth",
      lineErrorDescription ?? lineError,
    );
  }

  if (!code) {
    console.error("[auth/line/callback] missing authorization code");
    return loginErrorRedirect(request, "missing_code");
  }

  if (!validateOAuthState(state)) {
    console.error("[auth/line/callback] invalid OAuth state");
    return loginErrorRedirect(request, "invalid_state");
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
    const reason = error instanceof Error ? error.message : "unknown";
    console.error("[auth/line/callback] auth failed", { reason });
    return loginErrorRedirect(request, "auth_failed", reason);
  }
}
