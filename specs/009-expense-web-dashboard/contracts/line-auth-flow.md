# Contract: LINE Authentication Flow

**Feature**: 009-expense-web-dashboard  
**Runtime**: Next.js Route Handlers on Vercel (`web/src/app/api/auth/line/`)

## Overview

Two entry paths converge on the same server function `linkLineUserAndCreateSession(lineUserId, profile)`:

1. Upsert `auth.users` (email optional / synthetic `line-{userId}@users.line.local`)
2. Upsert `line_auth_identities`
3. Create Supabase session (cookie via `@supabase/ssr`)

## Path A — Browser LINE Login (OAuth 2.1)

```text
User → GET /login
     → redirect LINE authorize URL
       ?response_type=code
       &client_id={LINE_LOGIN_CHANNEL_ID}
       &redirect_uri={APP_URL}/api/auth/line/callback
       &state={csrf}
       &scope=profile openid
     → user approves
     → GET /api/auth/line/callback?code=...&state=...
     → server: exchange code at LINE token endpoint
     → server: verify ID token (iss, aud, exp, sub)
     → linkLineUserAndCreateSession(sub, profile)
     → redirect /dashboard
```

### LINE token endpoint

`POST https://api.line.me/oauth2/v2.1/token`

| Field | Value |
| ----- | ----- |
| grant_type | `authorization_code` |
| code | from callback |
| redirect_uri | must match authorize request |
| client_id | LINE Login Channel ID |
| client_secret | LINE Login Channel secret (server only) |

### ID token claims used

| Claim | Use |
| ----- | --- |
| `sub` | LINE `userId` → `line_auth_identities.line_user_id` |
| `name` | `display_name` (optional) |
| `picture` | `picture_url` (optional) |

## Path B — LIFF (in-app)

```text
User taps rich menu → LIFF endpoint /dashboard
     → client: liff.init({ liffId })
     → client: if !liff.isLoggedIn() → liff.login()
     → client: idToken = liff.getIDToken()
     → POST /api/auth/line/liff  { idToken }
     → server: verify ID token (LINE JWKS or verify API)
     → linkLineUserAndCreateSession(sub, profile)
     → return { ok: true } + Set-Cookie session
     → client: render dashboard
```

### LIFF client snippet (contract)

```typescript
await liff.init({ liffId: process.env.NEXT_PUBLIC_LINE_LIFF_ID! });
if (!liff.isLoggedIn()) {
  liff.login({ redirectUri: window.location.href });
}
const idToken = liff.getIDToken();
await fetch('/api/auth/line/liff', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ idToken }),
});
```

## Session management

- Use `@supabase/ssr` `createServerClient` in Route Handlers and middleware.
- Middleware (`web/src/middleware.ts`): refresh session; redirect unauthenticated `/dashboard` → `/login` (except LIFF bootstrap).
- Sign out: `supabase.auth.signOut()` + clear cookies → `/login`.

## CSRF / state

- OAuth `state` parameter: random nonce in httpOnly cookie, validated on callback.
- LIFF POST: same-site cookie + optional double-submit token.

## Error responses

| Condition | User-facing behavior |
| --------- | -------------------- |
| Invalid/expired ID token | Redirect `/login?error=auth_failed` |
| LINE token exchange failure | Same |
| Supabase admin failure | Generic error page; log server-side |
| Missing `sub` | Reject link |

## Security requirements

- **FR-012**: `LINE_LOGIN_CHANNEL_SECRET` and `SUPABASE_SERVICE_ROLE_KEY` only in Vercel server env.
- Verify ID token signature before trusting `sub`.
- Never accept raw `line_user_id` from client without token verification.

## Logout

`POST /api/auth/signout` or client `signOut()` — clears Supabase session; does not revoke LINE Login consent (acceptable for MVP).
