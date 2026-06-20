---
description: "Task list for Expense Web Dashboard feature implementation"
---

# Tasks: Expense Web Dashboard

**Input**: Design documents from `/specs/009-expense-web-dashboard/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Not explicitly requested in spec.md. Verification tasks are included in Foundational and Polish phases (RLS SQL fixtures, quickstart E2E checklist). No TDD test-first tasks.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the `web/` Next.js application scaffold per plan.md

- [x] T001 Create `web/` directory and initialize Next.js 15 App Router project with TypeScript and Tailwind CSS in `web/package.json`
- [x] T002 [P] Add `web/next.config.ts` with mobile-first defaults and environment variable exposure for `NEXT_PUBLIC_*` keys
- [x] T003 [P] Create `web/.env.example` documenting all variables from `specs/009-expense-web-dashboard/contracts/environment-variables.md`
- [x] T004 [P] Create `web/src/app/layout.tsx` with mobile viewport meta, base styles, and Japanese-friendly font stack
- [x] T005 [P] Create `web/src/app/page.tsx` to redirect authenticated users to `/dashboard` and others to `/login`
- [x] T006 [P] Add `web/tsconfig.json` and `web/tailwind.config.ts` aligned with Next.js 15 App Router conventions
- [x] T007 [P] Document Vercel root directory (`web/`) deployment note in `specs/009-expense-web-dashboard/quickstart.md` section 4 if not already explicit

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema, RLS, and shared auth/data libraries that MUST complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 Create Supabase migration `supabase/migrations/20260619120000_web_dashboard_auth_rls.sql` per `specs/009-expense-web-dashboard/contracts/supabase-schema-delta.md` (`line_auth_identities`, `current_line_user_id()`, RLS policies, grants)
- [x] T009 Apply migration to Supabase project and verify `current_line_user_id()` returns NULL in SQL editor when unauthenticated (document result in `specs/009-expense-web-dashboard/quickstart.md` section 2)
- [x] T010 [P] Implement browser Supabase client in `web/src/lib/supabase/client.ts` using `@supabase/ssr` `createBrowserClient`
- [x] T011 [P] Implement server Supabase client in `web/src/lib/supabase/server.ts` using `@supabase/ssr` `createServerClient` with cookie handlers
- [x] T012 [P] Implement session refresh helper in `web/src/lib/supabase/middleware.ts` for use by Next.js middleware
- [x] T013 [P] Implement LINE OAuth helpers in `web/src/lib/line/oauth.ts` (authorize URL builder, token exchange, CSRF `state` cookie helpers)
- [x] T014 [P] Implement LINE ID token verification in `web/src/lib/line/verify-id-token.ts` (issuer, audience, expiry, signature via LINE JWKS or verify API)
- [x] T015 Implement shared `linkLineUserAndCreateSession` in `web/src/lib/line/session.ts` (service-role upsert of `auth.users` + `line_auth_identities`, Supabase session cookie via `@supabase/ssr`)
- [x] T016 Implement `web/src/middleware.ts` to refresh Supabase session and guard `/dashboard` (redirect unauthenticated to `/login`, allow LIFF bootstrap path)
- [x] T017 [P] Create UI message catalogs in `web/src/lib/i18n/messages.ts` for `ja`, `en`, `zh` interface strings
- [x] T018 [P] Create locale helpers in `web/src/lib/i18n/locale.ts` (resolve `reply_language`, fallback to `ja`)
- [x] T019 [P] Create RLS verification SQL fixtures in `tests/web/rls_policies.test.sql` covering personal access, shared-ledger access, and cross-tenant denial cases

**Checkpoint**: Foundation ready — schema applied, shared libs in place, user story implementation can begin

---

## Phase 3: User Story 1 - Sign in with LINE (Priority: P1) 🎯 MVP

**Goal**: Users authenticate via LINE Login (browser) or LIFF (in-app) and receive a persistent Supabase session tied to their LINE `userId`

**Independent Test**: Open the dashboard URL, complete LINE sign-in (browser or LIFF), refresh the page, and confirm the session persists until logout or expiry. New users with no bot expenses see a friendly empty state, not an error.

### Implementation for User Story 1

- [x] T020 [P] [US1] Create `web/src/app/login/page.tsx` with mobile-first "Sign in with LINE" button redirecting to LINE OAuth authorize URL
- [x] T021 [P] [US1] Implement OAuth callback in `web/src/app/api/auth/line/callback/route.ts` per `specs/009-expense-web-dashboard/contracts/line-auth-flow.md` (validate `state`, exchange code, verify ID token, call `linkLineUserAndCreateSession`, redirect `/dashboard`)
- [x] T022 [P] [US1] Implement LIFF auth handler in `web/src/app/api/auth/line/liff/route.ts` (accept `{ idToken }`, verify server-side, call `linkLineUserAndCreateSession`, return session cookie)
- [x] T023 [US1] Wire CSRF `state` validation between `web/src/lib/line/oauth.ts` and `web/src/app/api/auth/line/callback/route.ts`
- [x] T024 [US1] Create `web/src/app/dashboard/page.tsx` shell with LIFF bootstrap (`liff.init`, `liff.login` fallback, POST to `/api/auth/line/liff`) and authenticated render path
- [x] T025 [US1] Implement sign-out flow clearing Supabase session cookies (client `signOut()` in dashboard and/or `web/src/app/api/auth/signout/route.ts`) redirecting to `/login`
- [x] T026 [US1] Add friendly empty-state UI in `web/src/app/dashboard/page.tsx` for authenticated users with no expenses (not a permission error)
- [x] T027 [US1] Add auth error handling redirecting to `/login?error=auth_failed` from callback and LIFF routes per `specs/009-expense-web-dashboard/contracts/line-auth-flow.md`
- [x] T028 [P] [US1] Create `web/src/components/LanguageProvider.tsx` React context wrapping dashboard and login pages
- [x] T029 [US1] Verify session persistence across page refresh via `web/src/middleware.ts` cookie refresh (manual check per quickstart)

**Checkpoint**: User Story 1 complete — sign-in, session, logout, and empty state work independently

---

## Phase 4: User Story 2 - View personal expense list (Priority: P1)

**Goal**: Signed-in users see their personal expenses in a mobile-friendly paginated list (date, description, JPY amount, category) ordered newest first

**Independent Test**: Log expenses via bot in 1:1 chat, sign into dashboard with personal ledger selected, verify list matches stored records (excluding soft-deleted items). UI chrome respects `user_language_preferences`.

### Implementation for User Story 2

- [x] T030 [P] [US2] Create expense query module in `web/src/lib/dashboard/expenses.ts` querying `v_expenses_enriched` per `specs/009-expense-web-dashboard/contracts/dashboard-read-api.md` (tenant filter, `currency = 'JPY'`, `deleted_at IS NULL`, order, range pagination)
- [x] T031 [P] [US2] Create `web/src/components/ExpenseList.tsx` with mobile-first row layout (date, description, ¥ amount, category chip)
- [x] T032 [US2] Integrate personal tenant default (`tenant_type = 'user'`, `tenant_id = line_user_id`) into `web/src/app/dashboard/page.tsx`
- [x] T033 [US2] Implement JPY amount formatting and JST date display helpers in `web/src/lib/dashboard/format.ts`
- [x] T034 [US2] Map category labels from `category_name_ja` / deepest non-null `category_lN_name` columns in `web/src/components/ExpenseList.tsx`
- [x] T035 [US2] Implement "Load more" pagination in `web/src/components/ExpenseList.tsx` (page size 20, stop when `data.length < pageSize`, no duplicate rows)
- [x] T036 [US2] Add loading spinner, empty state, and network-error retry affordance in `web/src/components/ExpenseList.tsx`
- [x] T037 [US2] Fetch `user_language_preferences.reply_language` on dashboard load in `web/src/app/dashboard/page.tsx` and apply via `web/src/components/LanguageProvider.tsx`

**Checkpoint**: User Story 2 complete — personal expense list is independently testable for signed-in users

---

## Phase 5: User Story 3 - Switch between personal and group ledgers (Priority: P1)

**Goal**: Users switch dashboard context between personal ledger and shared group/room ledgers where they are recorded in `tenant_chat_members`

**Independent Test**: Log expenses in a group via bot, sign in as a member, switch to that group tenant, and confirm only that group's shared expenses appear. Users with no group interaction see only personal option.

### Implementation for User Story 3

- [x] T038 [P] [US3] Create tenant query module in `web/src/lib/dashboard/tenants.ts` (implicit personal option + `tenant_chat_members` select ordered by `last_seen_at`)
- [x] T039 [P] [US3] Create `web/src/components/TenantSwitcher.tsx` compact mobile selector (scroll or dropdown for many groups)
- [x] T040 [US3] Integrate `TenantSwitcher` into `web/src/app/dashboard/page.tsx` with personal ledger as default selection
- [x] T041 [US3] Reload `ExpenseList` on tenant change in `web/src/app/dashboard/page.tsx` resetting offset and clearing prior rows
- [x] T042 [US3] Hide shared tenant options in `web/src/components/TenantSwitcher.tsx` when `tenant_chat_members` returns no rows
- [x] T043 [US3] Display generic i18n labels with shortened `tenant_id` suffix for group/room options in `web/src/components/TenantSwitcher.tsx`

**Checkpoint**: User Story 3 complete — tenant switching works without exposing unauthorized ledgers

---

## Phase 6: User Story 4 - Open dashboard from bot rich menu (Priority: P2)

**Goal**: Bot exposes a rich menu item that opens the dashboard via LIFF in the LINE in-app browser

**Independent Test**: Tap rich menu item in 1:1 bot chat; dashboard opens, LIFF auth completes, and expense list is reachable without manual URL entry.

### Implementation for User Story 4

- [x] T044 [P] [US4] Implement `scripts/setup_rich_menu.py` per `specs/009-expense-web-dashboard/contracts/rich-menu-setup.md` (create rich menu JSON, set default via Messaging API)
- [x] T045 [US4] Ensure LIFF entry path in `web/src/app/dashboard/page.tsx` handles `?source=line` and completes auth before rendering list
- [x] T046 [US4] Document LINE Console steps (Login callback URLs, LIFF app, rich menu) in `specs/009-expense-web-dashboard/quickstart.md` sections 1 and 5
- [x] T047 [US4] Configure Vercel project with root directory `web/` and all env vars from `specs/009-expense-web-dashboard/contracts/environment-variables.md`
- [x] T048 [US4] Run rich menu → LIFF → dashboard smoke test and record results in `specs/009-expense-web-dashboard/quickstart.md` section 6

**Checkpoint**: User Story 4 complete — primary mobile discovery path works end-to-end

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, verification, and cross-story improvements

- [x] T049 [P] Add `web/src/app/dashboard/error.tsx` error boundary with user-friendly message (no raw error codes)
- [x] T050 [P] Add structured server-side logging in `web/src/app/api/auth/line/callback/route.ts` and `web/src/app/api/auth/line/liff/route.ts` without PII
- [x] T051 Truncate or wrap very long expense descriptions in `web/src/components/ExpenseList.tsx` without horizontal scroll on phone-width viewports
- [x] T052 Confirm non-JPY rows are excluded by query filter in `web/src/lib/dashboard/expenses.ts` (MVP hides unsupported currency)
- [x] T053 Execute cross-tenant RLS denial checks using `tests/web/rls_policies.test.sql` and document pass/fail in `specs/009-expense-web-dashboard/quickstart.md` section 6
- [x] T054 Run full `specs/009-expense-web-dashboard/quickstart.md` validation (personal ledger, group ledger, language, security spot check)
- [x] T055 [P] Add smoke test for `scripts/setup_rich_menu.py` in existing pytest suite or `tests/test_setup_rich_menu.py` verifying API payload shape

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP auth gate
- **User Story 2 (Phase 4)**: Depends on US1 (requires authenticated session) — personal list only
- **User Story 3 (Phase 5)**: Depends on US2 components (`ExpenseList`, dashboard page) — adds tenant switching
- **User Story 4 (Phase 6)**: Depends on US1 LIFF path — can parallelize with US2/US3 after US1
- **Polish (Phase 7)**: Depends on desired user stories being complete

### User Story Dependencies

```text
Foundational (Phase 2)
        │
        ▼
   US1 Sign in (P1) ──────────────────────┐
        │                                  │
        ├──────────────► US2 Personal list (P1)
        │                      │
        │                      ▼
        │              US3 Tenant switch (P1)
        │
        └──────────────► US4 Rich menu (P2)
```

- **US1 (P1)**: No dependency on other stories; blocks US2–US4
- **US2 (P1)**: Requires US1 session; independently testable with personal ledger only
- **US3 (P1)**: Requires US2 list UI; independently testable by switching tenants
- **US4 (P2)**: Requires US1 LIFF auth; independently testable via rich menu tap

### Within Each User Story

- Shared libs (Phase 2) before route handlers and pages
- Auth routes before dashboard LIFF bootstrap (US1)
- Query modules before UI components (US2, US3)
- Script implementation before smoke test (US4)

### Parallel Opportunities

- Phase 1: T002–T007 can run in parallel after T001
- Phase 2: T010–T014, T017–T019 can run in parallel; T008 before T009; T015 after T011 and T014
- US1: T020–T022, T028 can run in parallel; T023–T027 sequential on shared auth flow
- US2: T030–T031 can run in parallel before T032 integration
- US3: T038–T039 can run in parallel before T040 integration
- US4: T044 can run in parallel with US2/US3 after US1
- Polish: T049–T050, T055 can run in parallel

---

## Parallel Example: User Story 1

```bash
# After Phase 2 completes, launch auth surfaces in parallel:
Task T020: "Create web/src/app/login/page.tsx"
Task T021: "Implement OAuth callback in web/src/app/api/auth/line/callback/route.ts"
Task T022: "Implement LIFF auth handler in web/src/app/api/auth/line/liff/route.ts"
Task T028: "Create web/src/components/LanguageProvider.tsx"

# Then wire integration sequentially:
Task T023 → T024 → T025 → T026 → T027 → T029
```

---

## Parallel Example: User Story 2 + 3 (after US1)

```bash
# Developer A — personal list:
Task T030: "expenses.ts query module"
Task T031: "ExpenseList.tsx component"
Task T032–T037: dashboard integration

# Developer B — tenant switcher (can start T038–T039 while A builds list):
Task T038: "tenants.ts query module"
Task T039: "TenantSwitcher.tsx component"
Task T040–T043: integrate after ExpenseList exists
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Sign in via browser and LIFF; confirm session persistence and empty state
5. Deploy to Vercel preview for auth testing

### Incremental Delivery

1. Setup + Foundational → schema and shared libs ready
2. US1 → LINE auth works → **MVP auth demo**
3. US2 → personal expense list → **MVP value demo**
4. US3 → group/room switching → full tenancy parity with bot
5. US4 → rich menu discovery → mobile-first launch path
6. Polish → security verification and quickstart sign-off

### Parallel Team Strategy

With multiple developers after Phase 2:

- **Developer A**: US1 auth routes and dashboard shell
- **Developer B**: US2 expense list (starts query module once US1 session helper exists)
- **Developer C**: Migration verification (T009, T019) + US4 rich menu script

---

## Notes

- `[P]` tasks = different files, no incomplete-task dependencies
- `[Story]` label maps tasks to user stories from `spec.md`
- `SUPABASE_SERVICE_ROLE_KEY` and `LINE_CHANNEL_SECRET` must never use `NEXT_PUBLIC_` prefix (FR-012)
- Bot webhook service is unchanged; only optional `scripts/setup_rich_menu.py` is added
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
