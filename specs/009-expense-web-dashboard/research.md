# Research: Expense Web Dashboard

**Feature**: 009-expense-web-dashboard  
**Date**: 2026-06-19

## R1: LINE authentication with Supabase Auth

**Decision**: Use **Supabase Auth sessions** with a **`line_auth_identities`** bridge table. LINE Login (OAuth 2.1 / OIDC) and LIFF ID tokens are verified in **Next.js Route Handlers** on Vercel; handlers call Supabase Admin API (service role, server-only) to create/link `auth.users` and insert/update `line_auth_identities`. Browser receives a normal Supabase session via `@supabase/ssr` cookies.

**Rationale**: User chose Supabase Auth and RLS over Edge Functions for MVP. Next.js on Vercel already provides a secure server runtime for LINE channel secret and token verification. Avoids shipping service role to client.

**Alternatives considered**:
- **Supabase Edge Function for OAuth callback** — valid, but adds Deno runtime + separate deploy; user preferred RLS-first with Vercel hosting.
- **Custom JWT only (no Supabase Auth)** — would not integrate cleanly with RLS `authenticated` role.
- **LINE as built-in Supabase social provider** — not available; LINE requires custom OIDC/OAuth wiring.

---

## R2: LIFF vs LINE Login coexistence

**Decision**: Support **both** entry paths sharing the same session issuance logic:
- **LIFF**: Rich menu opens LIFF endpoint URL → `liff.getIDToken()` → POST `/api/auth/line/liff`.
- **Browser**: `/login` → standard LINE Login authorization code flow → GET `/api/auth/line/callback`.

**Rationale**: Spec requires both mobile browser and in-app access. LIFF gives frictionless in-app UX; Login covers sharing the URL outside LINE.

**Alternatives considered**:
- **LIFF only** — rejects browser-only users.
- **Login only** — worse UX inside LINE in-app browser.

---

## R3: RLS authorization model

**Decision**: RLS policies on `expenses` (and view `v_expenses_enriched` via security invoker / underlying table policies) use a helper function:

```sql
current_line_user_id() → line_auth_identities.line_user_id WHERE auth_user_id = auth.uid()
```

Personal rows: `tenant_type = 'user' AND tenant_id = current_line_user_id()`.  
Shared rows: `tenant_type IN ('group','room')` AND `EXISTS` matching `tenant_chat_members` for `current_line_user_id()`.

**Rationale**: Avoids Supabase Custom Access Token Hook (Edge Function) for MVP. Mapping table is explicit and auditable. Reuses `tenant_chat_members` from feature 007 as membership source of truth.

**Alternatives considered**:
- **JWT custom claim `line_user_id`** — cleaner RLS SQL but requires Auth Hook Edge Function on every token refresh.
- **Edge Function BFF** — user deferred to future; more moving parts now.

---

## R4: Tenant list for switcher

**Decision**: Dashboard tenant options = **personal** (`user`, `line_user_id`) **union** `SELECT tenant_type, tenant_id FROM tenant_chat_members WHERE line_user_id = current_line_user_id()`.

**Rationale**: Matches spec FR-006 and bot semantics ("prior interactors"). No new membership table.

**Alternatives considered**:
- **Derive from `expenses.logged_by_line_user_id`** — misses groups where user interacted but did not log expenses.
- **LINE Group Membership API** — bots cannot list all members reliably in v1.

---

## R5: Expense list query shape

**Decision**: Query **`v_expenses_enriched`** with filters: `tenant_type`, `tenant_id`, `deleted_at IS NULL`, `currency = 'JPY'`, order `expense_date DESC, created_at DESC`, range pagination (20 rows).

**Rationale**: View already joins category names; avoids duplicate join logic in frontend. JPY filter matches MVP assumption.

**Alternatives considered**:
- **Direct `expenses` + client join** — more round trips.
- **PostgREST RPC** — unnecessary for simple filtered select under RLS.

---

## R6: Frontend framework on Vercel

**Decision**: **Next.js 15 (App Router) + React + TypeScript + Tailwind CSS** in `web/`.

**Rationale**: User chose "most convenient" framework (React/Next). First-class Vercel support, Route Handlers for OAuth, SSR for auth cookies, strong mobile CSS tooling.

**Alternatives considered**:
- **Vite SPA** — no built-in server routes for OAuth secret handling.
- **Vanilla JS** — faster bundle but more manual auth/session plumbing.

---

## R7: Internationalization

**Decision**: Static UI message catalogs for `ja`, `en`, `zh` in `web/src/lib/i18n/`. On dashboard load, fetch `user_language_preferences.reply_language` for signed-in user's `line_user_id`; fall back to `ja`. Category names use `category_name_ja` / enriched view columns (taxonomy remains Japanese-first; optional future localized category table out of scope).

**Rationale**: Aligns with bot `user_language_preferences` without blocking MVP on full category translation.

**Alternatives considered**:
- **Browser `Accept-Language` only** — ignores bot preference users already set.
- **Japanese-only UI** — conflicts with spec FR-009.

---

## R8: Rich menu discovery

**Decision**: Configure **one rich menu item** "Expenses" / 「家計簿」 opening the **LIFF URL** (or dashboard URL with `?source=line`). Provide `scripts/setup_rich_menu.py` using existing `LINE_CHANNEL_ACCESS_TOKEN` plus manual LINE Console steps in quickstart.

**Rationale**: Spec FR-010; LIFF URL gives best in-app auth. Same channel as bot per user decision.

**Alternatives considered**:
- **URI action to plain HTTPS** — works but may require extra Login redirect.
- **Bot message with link only** — no persistent discovery.

---

## R9: Same LINE channel for Login and Messaging

**Decision**: Enable **LINE Login** on the existing Messaging API channel; create **one LIFF app** bound to that channel; register Vercel callback URLs.

**Rationale**: User preference; fewer channels to manage. LINE Developers Console allows Login + Messaging on one channel when Login product is enabled.

**Alternatives considered**:
- **Separate Login channel** — more credential management without clear MVP benefit.

---

## R10: Security review notes

**Decision**:
- Verify LINE ID tokens server-side (issuer, audience, expiry, signature).
- Use `httpOnly` Supabase SSR cookies; protect `/dashboard` with middleware.
- RLS remains default-deny; only `authenticated` SELECT policies added.
- `line_auth_identities` INSERT/UPDATE only via service role in Route Handlers, not client.

**Rationale**: FR-007 and FR-012; expense data is sensitive financial information.

**Alternatives considered**:
- **Client-side ID token trust only** — rejected (forgable without verification).
