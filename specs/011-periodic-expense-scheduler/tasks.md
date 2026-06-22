---
description: "Task list for Periodic Expense Scheduler feature implementation"
---

# Tasks: Periodic Expense Scheduler

**Input**: Design documents from `/specs/011-periodic-expense-scheduler/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; features **009** and **010** complete

**Tests**: Not explicitly requested in spec.md. Recurrence engine Vitest tasks included per plan.md constitution compliance. RLS verification SQL in Foundational; manual cron checklist in Polish.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment, test runner, and module scaffolding for periodic expenses

- [x] T001 Add `CRON_SECRET` to `web/.env.example` and document in `specs/011-periodic-expense-scheduler/contracts/cron-processing.md`
- [x] T002 [P] Add Vitest dev dependency and `test` script in `web/package.json`; create `web/vitest.config.ts` for `src/lib/periodic/**/*.test.ts`
- [x] T003 [P] Create recurrence type definitions in `web/src/lib/periodic/types.ts` per `specs/011-periodic-expense-scheduler/data-model.md` (RecurrenceRule union, EndKind, ScheduleStatus)
- [x] T004 [P] Add periodic-expenses i18n key placeholders in `web/src/lib/i18n/messages.ts` (`navPeriodicExpenses`, form labels, recurrence summaries, status badges)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema, recurrence engine, cron processor, and shared server helpers that MUST complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create Supabase migration `supabase/migrations/20260623120000_periodic_expense_schedules.sql` per `specs/011-periodic-expense-scheduler/contracts/supabase-schema-delta.md` (`periodic_expense_schedules` table, `expenses.periodic_schedule_id`, indexes, RLS policies, category-delete trigger)
- [x] T006 Implement `process_due_periodic_schedules(p_as_of timestamptz)` RPC in the same migration file (due selection, end checks, expense insert with synthetic `source_message_id`, counter updates, idempotent unique index)
- [x] T007 Apply migration to Supabase project and verify `periodic_expense_schedules` RLS enabled (document in `specs/011-periodic-expense-scheduler/quickstart.md`)
- [x] T008 [P] Implement `computeNextRunDate` and recurrence helpers in `web/src/lib/periodic/recurrence.ts` covering all five kinds (interval_days, monthly_days, monthly_boundary, every_n_months, every_n_weeks) plus month-end/leap-year edge cases from spec
- [x] T009 [P] Implement request validation helpers in `web/src/lib/periodic/validation.ts` (amount > 0, end_kind field requirements, recurrence JSON schema)
- [x] T010 [P] Implement `formatRecurrenceSummary` and status label helpers in `web/src/lib/periodic/format.ts` returning i18n keys or localized strings
- [x] T011 Create Vitest matrix in `web/src/lib/periodic/recurrence.test.ts` for FR-003–FR-007 scenarios (20-day interval, monthly 1st/15th, first/last boundary, every 3 months on 10th, every 3 weeks on Wednesday, Feb 31 → last day)
- [x] T012 [P] Implement cron route `web/src/app/api/cron/process-periodic-expenses/route.ts` with `CRON_SECRET` bearer check and service-role RPC call via `web/src/lib/supabase/admin.ts`
- [x] T013 [P] Add hourly cron entry to `web/vercel.json` per `specs/011-periodic-expense-scheduler/contracts/cron-processing.md` (`0 * * * *` on `/api/cron/process-periodic-expenses`)
- [x] T014 [P] Create shared server helper `web/src/lib/periodic/server.ts` (resolve category L1/L2 IDs from tenant taxonomy, compute initial `next_run_date`, map DB row to API response shape)
- [x] T015 [P] Create RLS verification SQL fixtures in `tests/web/periodic_schedules_rls.test.sql` (personal owner access, group member access, cross-tenant denial)
- [x] T016 [P] Create tenant authorization helper `web/src/lib/periodic/tenant-access.ts` mirroring categories API (validate `tenant_type`/`tenant_id` against `current_line_user_id()` and `tenant_chat_members`)

**Checkpoint**: Foundation ready — schema applied, recurrence engine tested, cron route callable locally

---

## Phase 3: User Story 1 - Create a basic periodic expense (Priority: P1) 🎯 MVP

**Goal**: Signed-in user creates a schedule with name, L1/L2 category, amount, recurrence, and start date; it appears in the list as active with next run date

**Independent Test**: Create a monthly rent schedule for personal tenant; confirm saved schedule shows correct amount, category, frequency label, and `next_run_date` via GET list API or UI

### Implementation for User Story 1

- [x] T017 [P] [US1] Implement `GET` and `POST` handlers in `web/src/app/api/periodic-expenses/route.ts` per `specs/011-periodic-expense-scheduler/contracts/periodic-expenses-api.md` (tenant query params, validation, `next_run_date` computation, `created_by_line_user_id`)
- [x] T018 [P] [US1] Create `web/src/components/periodic/ScheduleForm.tsx` with name, amount, category picker (L1/L2), start date, and default monthly recurrence fields
- [x] T019 [US1] Wire category options in `ScheduleForm.tsx` via existing `GET /api/categories` (lazy-init tenant taxonomy from 010)
- [x] T020 [US1] Create `web/src/app/(app)/periodic-expenses/page.tsx` shell with `TenantSwitcher`, create button opening `ScheduleForm`, and fetch on tenant change
- [x] T021 [US1] Add client-side validation and error display in `ScheduleForm.tsx` (empty name, zero amount, missing category/recurrence)
- [x] T022 [US1] Add i18n strings for create form and validation errors in `web/src/lib/i18n/messages.ts` (ja/en/zh)

**Checkpoint**: User Story 1 complete — user can create a basic schedule for personal tenant via web UI

---

## Phase 4: User Story 2 - Flexible recurrence rules (Priority: P1)

**Goal**: User configures interval days, monthly days/boundaries, every N months, and every N weeks on weekdays; list shows human-readable frequency summary

**Independent Test**: Create three schedules — every 20 days, every 3 months on 15th, every 2 weeks on Monday — verify `recurrence_summary` and correct `next_run_date` on each

### Implementation for User Story 2

- [x] T023 [P] [US2] Create `web/src/components/periodic/RecurrenceFields.tsx` with UI for all five recurrence kinds and param inputs (N, days[], boundary, weekdays[])
- [x] T024 [US2] Integrate `RecurrenceFields.tsx` into `web/src/components/periodic/ScheduleForm.tsx` with kind selector and controlled recurrence state
- [x] T025 [P] [US2] Implement optional `POST /api/periodic-expenses/preview-next` route in `web/src/app/api/periodic-expenses/preview-next/route.ts` for live next-date preview in form
- [x] T026 [US2] Wire `formatRecurrenceSummary` into list API response in `web/src/app/api/periodic-expenses/route.ts` and display on schedule rows/cards

**Checkpoint**: User Story 2 complete — all recurrence kinds creatable with correct next-run computation

---

## Phase 5: User Story 3 - End conditions (Priority: P1)

**Goal**: User sets end never, on date, amount cap, or repeat count; ended schedules stop logging and show ended status

**Independent Test**: Create schedules with each end type; after sufficient cron runs, confirm status `ended` and no further expenses logged

### Implementation for User Story 3

- [x] T027 [P] [US3] Create `web/src/components/periodic/EndConditionFields.tsx` with end_kind selector and conditional fields (`end_date`, `end_amount_cap`, `end_repeat_limit`)
- [x] T028 [US3] Integrate `EndConditionFields.tsx` into `web/src/components/periodic/ScheduleForm.tsx` and include end fields in POST/PATCH payloads
- [x] T029 [US3] Extend `web/src/lib/periodic/validation.ts` and API routes to enforce end_kind field requirements (400 on mismatch)
- [x] T030 [US3] Verify RPC `process_due_periodic_schedules` end checks in migration: on_date, amount_cap (no partial over-cap occurrence), repeat_count; set `status = ended` and `next_run_date = NULL`

**Checkpoint**: User Story 3 complete — all four end conditions enforced in UI and cron processor

---

## Phase 6: User Story 4 - Pause, restart, edit, and delete (Priority: P1)

**Goal**: User pauses, restarts, edits, or deletes schedules; ended schedules require end-condition edit to restart

**Independent Test**: Pause weekly schedule (no cron expense), restart (next run recalculated), edit amount, delete schedule (prior expenses remain)

### Implementation for User Story 4

- [x] T031 [P] [US4] Implement `GET` and `PATCH` in `web/src/app/api/periodic-expenses/[id]/route.ts` (partial update, recalc `next_run_date`, optional reactivate from ended)
- [x] T032 [P] [US4] Implement `POST` pause handler in `web/src/app/api/periodic-expenses/[id]/pause/route.ts` (`status = paused`, `pause_reason = user`, 409 if already paused/ended)
- [x] T033 [P] [US4] Implement `POST` restart handler in `web/src/app/api/periodic-expenses/[id]/restart/route.ts` (recalc from today, 409 for ended without end edit, block if `pause_reason = category_missing`)
- [x] T034 [US4] Implement `DELETE` handler in `web/src/app/api/periodic-expenses/[id]/route.ts` (204, does not delete linked expenses)
- [x] T035 [US4] Add edit mode to `web/src/components/periodic/ScheduleForm.tsx` (pre-fill from existing schedule, PATCH on save)
- [x] T036 [US4] Add pause/restart/delete action buttons on schedule cards calling respective API routes with confirm dialog on delete

**Checkpoint**: User Story 4 complete — full schedule lifecycle manageable from UI

---

## Phase 7: User Story 5 - Group and personal tenant scope (Priority: P1)

**Goal**: Schedules scoped to personal or group/room ledger via tenant switcher; group members share CRUD access; unauthorized tenants denied

**Independent Test**: User A creates group schedule; user B (same group) sees it; user C does not access group tenant

### Implementation for User Story 5

- [x] T037 [US5] Ensure all periodic API routes in `web/src/app/api/periodic-expenses/` call `web/src/lib/periodic/tenant-access.ts` before reads/writes
- [x] T038 [US5] Persist selected tenant from `TenantSwitcher` on `web/src/app/(app)/periodic-expenses/page.tsx` (URL search param or shared context pattern from dashboard/categories)
- [x] T039 [US5] Scope `GET /api/periodic-expenses` list query to selected `tenant_type`/`tenant_id` only
- [x] T040 [US5] Run and document RLS fixtures from `tests/web/periodic_schedules_rls.test.sql` for group member vs non-member cases in `specs/011-periodic-expense-scheduler/quickstart.md`

**Checkpoint**: User Story 5 complete — tenant isolation matches expenses/categories model

---

## Phase 8: User Story 6 - Automatic occurrence logging (Priority: P1)

**Goal**: Due active schedules log one expense per day with correct amount, category, description, and attribution; counters advance; paused/ended skip

**Independent Test**: Create schedule with `start_date = today`; curl cron route; confirm expense in dashboard list and schedule counters updated

### Implementation for User Story 6

- [x] T041 [US6] Verify RPC expense insert sets `periodic_schedule_id`, `source_message_id = periodic:{id}:{date}`, category FKs, and `logged_by_line_user_id = created_by_line_user_id` in `supabase/migrations/20260623120000_periodic_expense_schedules.sql`
- [x] T042 [US6] Add structured logging (counts only, no PII) to `web/src/app/api/cron/process-periodic-expenses/route.ts`
- [x] T043 [US6] Document local cron test procedure in `specs/011-periodic-expense-scheduler/quickstart.md` (curl with `CRON_SECRET`, verify dashboard expense row)
- [x] T044 [US6] Add SQL or documented manual test for idempotent double cron run (second run `skipped`, no duplicate expense) in `tests/web/periodic_schedules_rls.test.sql` or quickstart troubleshooting table

**Checkpoint**: User Story 6 complete — auto-logging end-to-end verified locally

---

## Phase 9: User Story 7 - Card list overview (Priority: P2)

**Goal**: Scannable mobile cards with emphasized amount, name, frequency, category path, next run or status badge, and quick actions

**Independent Test**: With 5+ mixed schedules (active/paused/ended), verify amount visually dominant and key fields readable without opening detail

### Implementation for User Story 7

- [x] T045 [P] [US7] Create `web/src/components/periodic/ScheduleCard.tsx` with highlighted amount typography, frequency summary, category path (L1 › L2), next run date, paused/ended badges
- [x] T046 [US7] Create `web/src/components/periodic/ScheduleCardList.tsx` replacing raw list on `web/src/app/(app)/periodic-expenses/page.tsx` (sort by `next_run_date ASC NULLS LAST`)
- [x] T047 [US7] Add empty state CTA and loading/error retry UI in `ScheduleCardList.tsx`
- [x] T048 [US7] Enrich GET list response with `category_l1_name` / `category_l2_name` joins in `web/src/lib/periodic/server.ts`

**Checkpoint**: User Story 7 complete — card list meets spec UX requirements

---

## Phase 10: User Story 8 - Navigation entry (Priority: P2)

**Goal**: Periodic Expenses reachable from side drawer; tenant selection preserved across navigation

**Independent Test**: Open drawer from dashboard, tap Periodic Expenses, confirm route loads with same tenant selected

### Implementation for User Story 8

- [x] T049 [P] [US8] Add `navPeriodicExpenses` link to `NAV_ITEMS` in `web/src/components/SideDrawer.tsx` pointing to `/periodic-expenses`
- [x] T050 [US8] Ensure `web/src/middleware.ts` protects `/periodic-expenses` same as `/dashboard` and `/categories` (redirect unauthenticated to `/login`)
- [x] T051 [US8] Highlight active route for `/periodic-expenses` in `web/src/components/SideDrawer.tsx`

**Checkpoint**: User Story 8 complete — navigation discoverable and consistent

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Category-delete integration, i18n completeness, and quickstart validation

- [x] T052 [P] Display `pause_reason = category_missing` message on `web/src/components/periodic/ScheduleCard.tsx` with prompt to reassign category via edit form (FR-020)
- [x] T053 [P] Complete ja/en/zh translations for all periodic strings in `web/src/lib/i18n/messages.ts` (recurrence summaries, end kinds, empty states)
- [x] T054 Run full manual checklist in `specs/011-periodic-expense-scheduler/quickstart.md` (create, cron, pause, group tenant, end conditions)
- [x] T055 [P] Add Vercel production note for `CRON_SECRET` and cron logs to `specs/011-periodic-expense-scheduler/quickstart.md` deploy section

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Stories (Phases 3–10)**: All depend on Foundational completion
  - US1–US6 are P1; US7–US8 are P2
  - Recommended sequential order: US1 → US2 → US3 → US4 → US5 → US6 → US7 → US8
  - US8 can start in parallel with US7 after US1 page exists
- **Polish (Phase 11)**: Depends on US1–US8

### User Story Dependencies

| Story | Depends on | Notes |
| ----- | ---------- | ----- |
| US1 | Foundational | MVP — basic create + page shell |
| US2 | US1 (form exists) | Extends ScheduleForm recurrence |
| US3 | US1 | Adds end fields to form + RPC |
| US4 | US1, US3 | Lifecycle APIs + card actions |
| US5 | US1 | Tenant scoping on existing routes/page |
| US6 | Foundational (RPC/cron) | Verification phase |
| US7 | US1, US4 | Cards need list data + actions |
| US8 | US1 (page route) | Drawer link only |

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 in parallel
- **Phase 2**: T008–T011, T012–T016 in parallel after T005–T006 migration drafted
- **US1**: T017, T018 in parallel
- **US2**: T023, T025 in parallel
- **US3**: T027 parallel with T029 prep
- **US4**: T031, T032, T033 in parallel
- **US7**: T045 parallel with T048
- **US8**: T049 parallel with US7 card work
- **Polish**: T052, T053, T055 in parallel

---

## Parallel Example: Foundational Phase

```bash
# After migration SQL drafted (T005–T006), launch in parallel:
Task T008: recurrence.ts
Task T009: validation.ts
Task T010: format.ts
Task T012: cron route
Task T013: vercel.json
Task T014: server.ts helper
Task T015: RLS SQL fixtures
Task T016: tenant-access.ts
# Then T011 Vitest after T008 completes
```

---

## Parallel Example: User Story 4

```bash
# Lifecycle API routes (different files):
Task T031: PATCH/GET [id]/route.ts
Task T032: pause/route.ts
Task T033: restart/route.ts
# Then T034 DELETE + T035–T036 UI integration
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Create monthly schedule via UI; confirm in API/DB
5. Deploy/demo if ready (cron not required for create-only demo)

### Core Value (P1 stories)

1. Setup + Foundational → engine + schema + cron ready
2. US1 + US2 + US3 → full schedule configuration
3. US4 → lifecycle management
4. US5 → group parity
5. US6 → verify auto-logging (feature complete for P1)
6. US7 + US8 → UX polish (P2)

### Incremental Delivery

Each story adds testable value without breaking prior stories. Cron (US6) can ship after US1–US3 even if US4 UI is incomplete (schedules still fire).

---

## Notes

- Recurrence engine (`recurrence.ts`) lives in Foundational because US1–US3 all depend on it
- Cron processor is Foundational infrastructure; US6 is verification-focused
- Bot code unchanged — all writes from web API and cron RPC only
- Use `web/src/lib/supabase/admin.ts` for cron; never expose service role to client
- Commit after each phase checkpoint
