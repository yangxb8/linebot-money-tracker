import { createHmac, randomBytes, timingSafeEqual } from "crypto";

const STATE_TTL_MS = 10 * 60 * 1000;

export function lineSyntheticEmail(lineUserId: string): string {
  return `line-${lineUserId}@users.line.local`;
}

function appUrl(): string {
  return process.env.NEXT_PUBLIC_APP_URL!.replace(/\/$/, "");
}

function lineLoginChannelId(): string {
  return process.env.LINE_LOGIN_CHANNEL_ID!.trim();
}

function lineLoginChannelSecret(): string {
  const secret = process.env.LINE_LOGIN_CHANNEL_SECRET?.trim();
  if (!secret) {
    throw new Error("LINE_LOGIN_CHANNEL_SECRET is not configured");
  }
  return secret;
}

export function buildLineAuthorizeUrl(state: string): string {
  const params = new URLSearchParams({
    response_type: "code",
    client_id: lineLoginChannelId(),
    redirect_uri: `${appUrl()}/api/auth/line/callback`,
    state,
    scope: "profile openid",
  });

  // bot_prompt requires a linked LINE Official Account on the Login channel.
  // Set LINE_LOGIN_BOT_PROMPT=normal only after linking in LINE Console.
  const botPrompt = process.env.LINE_LOGIN_BOT_PROMPT;
  if (botPrompt === "normal" || botPrompt === "aggressive") {
    params.set("bot_prompt", botPrompt);
  }

  return `https://access.line.me/oauth2/v2.1/authorize?${params.toString()}`;
}

export function createOAuthState(): string {
  const nonce = randomBytes(16).toString("hex");
  const issuedAt = Date.now().toString(36);
  const payload = `${nonce}.${issuedAt}`;
  const sig = createHmac("sha256", lineLoginChannelSecret())
    .update(payload)
    .digest("hex");
  return `${payload}.${sig}`;
}

export function validateOAuthState(state: string | null): boolean {
  if (!state) return false;

  const parts = state.split(".");
  if (parts.length !== 3) return false;

  const [nonce, issuedAt, sig] = parts;
  if (!nonce || !issuedAt || !sig) return false;

  const payload = `${nonce}.${issuedAt}`;
  const expected = createHmac("sha256", lineLoginChannelSecret())
    .update(payload)
    .digest("hex");

  const expectedBuf = Buffer.from(expected, "hex");
  let actualBuf: Buffer;
  try {
    actualBuf = Buffer.from(sig, "hex");
  } catch {
    return false;
  }

  if (
    expectedBuf.length !== actualBuf.length ||
    !timingSafeEqual(expectedBuf, actualBuf)
  ) {
    return false;
  }

  const age = Date.now() - Number.parseInt(issuedAt, 36);
  return Number.isFinite(age) && age >= 0 && age <= STATE_TTL_MS;
}

export async function exchangeCodeForTokens(code: string): Promise<{
  id_token: string;
  access_token: string;
}> {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: `${appUrl()}/api/auth/line/callback`,
    client_id: lineLoginChannelId(),
    client_secret: lineLoginChannelSecret(),
  });

  const response = await fetch("https://api.line.me/oauth2/v2.1/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `LINE token exchange failed: ${response.status} ${detail.slice(0, 200)}`,
    );
  }

  return response.json();
}
