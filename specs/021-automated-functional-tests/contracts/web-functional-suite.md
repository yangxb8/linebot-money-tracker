# Contract: Web Functional Suite

**Feature**: 021-automated-functional-tests  
**Surfaces**: Next.js App Router API routes + minimal browser smoke  
**Lane**: `pr_fast`

## A. API / route functional tests (Vitest)

### Auth simulation

- Mock `createClient` / `auth.getUser` (or domain `require*User`) to return a fixed test user **or** null.
- Mock tenant-scoped data access with in-memory fakes — no live Supabase.
- Invoke exported HTTP handlers with `new Request(url, { method, headers, body })`.

### Representative routes (existing product surface)

| Scenario id | Route(s) | Contract |
| ----------- | -------- | -------- |
| `web.api.unauthorized` | Any protected route, e.g. `GET /api/expenses` | `401` when `getUser` is null |
| `web.api.expenses_overview` | `GET /api/expenses` (and/or fiscal helpers as used by overview) | `200`; body includes list or empty collection shape |
| `web.api.wish_list_mutate` | `POST /api/wish-list` then `GET /api/wish-list` (or GET by id) | Create succeeds; subsequent read includes item |
| `web.api.settings_bot_behavior` | `GET/PATCH` (or PUT) `/api/settings` | Save bot-behavior fields; reload returns same values |
| `web.api.budgets` | `GET/PUT` (or POST) `/api/budgets` | Read/update succeeds; returned state matches write |
| `web.api.categories` | `POST /api/categories` then list/get | Create/update visible on subsequent read |

Exact method verbs follow current route implementations under `web/src/app/api/**`.

### Assertion style

- Prefer status codes + JSON field presence / equality on stable identifiers.
- Do not require live LINE Login cookies.

## B. Browser smoke (Playwright)

### Environment

- Base URL: local `next dev`/`next start` **or** Playwright `webServer` config.
- Provide stub `NEXT_PUBLIC_SUPABASE_*` so middleware can construct a client; stub `getUser` / browser auth so no real project is required.
- Intercept or mock network calls that would hit Supabase Auth/REST.

### Scenarios

| Scenario id | Steps | Expect |
| ----------- | ----- | ------ |
| `web.browser.auth_gate` | Open `/dashboard` (or `/wish-list`) with no session | Navigate to `/login` (via `AppAuthProvider` or equivalent); no private ledger content |
| `web.browser.signed_in_smoke` | Mock signed-in `getUser`; open `/dashboard` | URL stays on app route; page renders without auth bounce |

### Non-goals (v1)

- LINE Login OAuth UI automation
- Full CRUD through the browser for wish list/budgets/categories
- Periodic-expense pages

## Local commands

```bash
cd web && npm test -- --run   # includes *.functional.test.ts once configured
cd web && npx playwright test # smoke only
```
