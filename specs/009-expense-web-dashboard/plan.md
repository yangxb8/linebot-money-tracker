# Implementation Plan: Expense Web Dashboard

**Branch**: `009-expense-web-dashboard` | **Date**: 2026-06-19 | **Spec**: [spec.md](./spec.md)

**Input**: Mobile-first read-only expense dashboard for LINE bot users. LINE Login + LIFF authentication via Supabase Auth; Next.js on Vercel; direct Supabase JS reads with new RLS policies. Personal and group/room tenant switcher. Rich menu entry on bot. Builds on **004–007** expense and tenancy features.

## Summary

Add a **`web/`** Next.js application deployed to Vercel that authenticates LINE users through Supabase Auth (browser OAuth + LIFF ID token), maps sessions to existing `line_user_id` keys, and displays a paginated read-only expense list from `v_expenses_enriched`. Introduce **`line_auth_identities`** plus **RLS policies** on `expenses`, `category_nodes`, and `tenant_chat_members` so the browser uses only the Supabase anon/publishable key. OAuth token exchange runs in **Next.js Route Handlers** on Vercel (channel secret stays server-side). Bot gains a **rich menu** script/docs pointing to the LIFF or dashboard URL.

## Technical Context

**Language/Version**: TypeScript / Node 20+ (Next.js 15 App Router); Python 3.11+ bot unchanged except optional rich-menu setup script

**Primary Dependencies**: Next.js, React, `@supabase/supabase-js`, `@supabase/ssr`, `@line/liff`, LINE Login OAuth 2.1 / OpenID Connect; existing `supabase` Python client for bot

**Storage**: Supabase Postgres (existing project) — new `line_auth_identities`; RLS policies on existing tables; read via `v_expenses_enriched`

**Testing**: Vitest or Jest for web utilities; Playwright or manual mobile checklist for auth flows; pytest unchanged for bot; RLS policy verification via SQL integration tests or documented manual queries

**Target Platform**: Vercel (`*.vercel.app`) + LINE in-app browser (LIFF) + mobile Safari/Chrome; Supabase hosted Postgres

**Project Type**: Monorepo extension — Python bot service + new `web/` frontend

**Performance Goals**: First expense page visible ≤3s on typical mobile LTE; auth redirect round-trip ≤5s; pagination fetch ≤1s p95 for 20-row pages

**Constraints**:
- Service role key MUST NOT ship to browser (FR-012)
- Read-only MVP — no expense mutations from web
- RLS MUST enforce tenant isolation (FR-007)
- JPY-only display filter in UI layer
- Same LINE channel for Messaging API and Login

**Scale/Scope**: Household users (<10 groups per user); lists up to low thousands of rows per tenant; single Vercel preview/production deployment for MVP

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | New `web/` app with clear `lib/supabase`, `lib/line`, feature folders; RLS in migration SQL; reuse `tenant_chat_members` |
| Test-First Delivery | RLS policy tests / documented SQL verification; web auth callback unit tests; bot rich-menu script smoke test |
| User Experience Consistency | Reuse `ja`/`en`/`zh` language codes; mobile-first list layout; empty states match bot tone |
| Performance & Reliability | Paginated queries; indexed tenant+date filters; graceful loading/error states |
| Observability & Feedback | Client-side error boundaries; structured logs in Next.js auth routes; no PII in client logs |
| Secrets | LINE channel secret + Supabase service role only in Vercel env / server routes |

**Post-design re-check**: PASS

## Architecture

```text
┌─────────────────┐     LIFF / LINE Login     ┌──────────────────────┐
│  Mobile browser │ ────────────────────────► │  Vercel (Next.js)    │
│  LINE in-app    │                           │  /login, /dashboard  │
└────────┬────────┘                           │  /api/auth/line/*    │
         │                                    └──────────┬───────────┘
         │  Supabase JS (anon key + session JWT)         │ server-side
         ▼                                               ▼ OAuth exchange
┌─────────────────────────────────────────────────────────────────────┐
│  Supabase                                                           │
│  Auth (sessions) │ line_auth_identities │ RLS on expenses/view     │
│  tenant_chat_members (read) │ category_nodes (read)                  │
└─────────────────────────────────────────────────────────────────────┘
         ▲
         │ service role (unchanged)
┌────────┴────────┐
│  LINE bot       │  rich menu → dashboard LIFF URL
│  Cloud Run      │
└─────────────────┘
```

### Auth flow (dual entry)

1. **Browser (LINE Login)**: User → `/login` → redirect to LINE OAuth → callback `/api/auth/line/callback` → exchange code for tokens → verify ID token `sub` = LINE userId → upsert `auth.users` + `line_auth_identities` → Supabase session cookie.
2. **LIFF**: User opens LIFF URL from rich menu → `liff.init()` → `liff.getIDToken()` → POST `/api/auth/line/liff` → verify JWT with LINE → same upsert + session.
3. **Subsequent requests**: `@supabase/ssr` refreshes session; RLS resolves `auth.uid()` → `line_user_id` via `line_auth_identities`.

### Data read flow

1. Dashboard loads user tenants: personal + rows from `tenant_chat_members` for user's `line_user_id`.
2. Selected tenant drives query on `v_expenses_enriched` filtered by `tenant_type`, `tenant_id`, `deleted_at IS NULL`, `currency = 'JPY'`, ordered `expense_date DESC`, page size 20.
3. RLS on underlying `expenses` enforces same rules server-side.

## Project Structure

### Documentation (this feature)

```text
specs/009-expense-web-dashboard/
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
└── contracts/
    ├── supabase-schema-delta.md
    ├── line-auth-flow.md
    ├── dashboard-read-api.md
    ├── environment-variables.md
    └── rich-menu-setup.md
```

### Source Code (repository root)

```text
web/                              # NEW — Vercel project root
├── package.json
├── next.config.ts
├── vercel.json                   # optional: root directory hint if needed
├── .env.example
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # redirect → /dashboard or /login
│   │   ├── login/page.tsx
│   │   ├── dashboard/page.tsx
│   │   └── api/auth/line/
│   │       ├── callback/route.ts
│   │       └── liff/route.ts
│   ├── components/
│   │   ├── ExpenseList.tsx
│   │   ├── TenantSwitcher.tsx
│   │   └── LanguageProvider.tsx
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts
│   │   │   ├── server.ts
│   │   │   └── middleware.ts
│   │   ├── line/
│   │   │   ├── oauth.ts
│   │   │   └── verify-id-token.ts
│   │   └── i18n/
│   │       ├── messages.ts       # ja/en/zh UI strings
│   │       └── locale.ts
│   └── middleware.ts             # session refresh + auth guard
├── public/
scripts/
  setup_rich_menu.py              # NEW optional — create rich menu via LINE API
supabase/migrations/
  20260619120000_web_dashboard_auth_rls.sql
tests/web/                        # NEW — optional vitest
  rls_policies.test.sql           # or documented in quickstart
```

**Structure Decision**: Add `web/` as a sibling to the Python bot; no changes to core bot message handling except optional rich-menu deployment script and documentation.

## Implementation Approach

### Phase A — Schema & RLS (P1)

1. Migration: `line_auth_identities`, enable RLS policies (see [contracts/supabase-schema-delta.md](./contracts/supabase-schema-delta.md)).
2. Grant `SELECT` on `v_expenses_enriched`, `category_nodes`, `tenant_chat_members` to `authenticated`.
3. Verify cross-tenant denial with SQL fixtures.

### Phase B — Next.js scaffold & auth (P1)

1. `create-next-app` in `web/` with App Router, TypeScript, Tailwind (mobile-first).
2. Supabase SSR cookie helpers; env wiring per [contracts/environment-variables.md](./contracts/environment-variables.md).
3. LINE OAuth callback + LIFF token routes per [contracts/line-auth-flow.md](./contracts/line-auth-flow.md).
4. Login page (browser) + LIFF auto-auth path on dashboard entry.

### Phase C — Dashboard read UI (P1)

1. Tenant switcher (personal + `tenant_chat_members`).
2. Paginated expense list per [contracts/dashboard-read-api.md](./contracts/dashboard-read-api.md).
3. i18n for UI chrome; load `user_language_preferences.reply_language` when present.
4. Empty, loading, and error states.

### Phase D — Bot discovery (P2)

1. Configure LIFF app + callback URLs in LINE Console.
2. `scripts/setup_rich_menu.py` or manual steps per [contracts/rich-menu-setup.md](./contracts/rich-menu-setup.md).
3. Deploy to Vercel; smoke test rich menu → LIFF → list.

## Complexity Tracking

| Item | Why Needed | Simpler Alternative Rejected Because |
| ---- | ---------- | ------------------------------------ |
| Next.js Route Handlers for LINE OAuth | LINE channel secret cannot live in browser | Pure client-side LINE Login — exposes secret |
| `line_auth_identities` mapping table | Supabase `auth.users.id` ≠ LINE userId | Storing LINE ID only in JWT custom hook — extra Edge Function dependency for MVP |
| Dual auth paths (Login + LIFF) | Users arrive from browser and in-app rich menu | LIFF-only — fails outside LINE app |

No constitution violations requiring waiver.
