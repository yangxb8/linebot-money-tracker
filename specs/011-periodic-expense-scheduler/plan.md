# Implementation Plan: Periodic Expense Scheduler

**Branch**: `011-periodic-expense-scheduler` | **Date**: 2026-06-23 | **Spec**: [spec.md](./spec.md)

**Input**: Web console feature to create, manage, and automatically execute recurring expense schedules for personal and group/room ledgers — flexible recurrence, end conditions, pause/restart, card list UI, daily batch logging into the existing expense ledger.

## Summary

Add a **`periodic_expense_schedules`** table (tenant-scoped, RLS) plus optional **`periodic_schedule_id`** FK on **`expenses`** for idempotent occurrence tracking. A shared **recurrence engine** (TypeScript) computes `next_run_date` for five rule kinds and powers both the create/edit form preview and the cron processor. **Vercel Cron** (hourly) invokes a secured **`/api/cron/process-periodic-expenses`** route using the Supabase **service role** to call RPC **`process_due_periodic_schedules`**, which atomically inserts expenses and advances or ends schedules. Web UI adds **`/periodic-expenses`** with card list + create/edit sheet, drawer nav entry, and **`/api/periodic-expenses/*`** route handlers mirroring the categories API pattern.

## Technical Context

**Language/Version**: TypeScript / Node 20+ (Next.js 15 App Router); SQL (Supabase Postgres migrations)

**Primary Dependencies**: Next.js, `@supabase/supabase-js`, `@supabase/ssr`, Vercel Cron; existing tenant switcher, categories API, RLS helpers from 009/010

**Storage**: Supabase Postgres — new `periodic_expense_schedules`; `expenses.periodic_schedule_id` nullable FK; RPC for batch processing; RLS on schedules

**Testing**: Vitest for `lib/periodic/recurrence.ts` (all rule kinds + edge cases); Vitest/integration for API routes; SQL tests for RPC idempotency and RLS deny; manual cron trigger via `curl` in quickstart

**Target Platform**: Vercel (`web/`) + Supabase hosted Postgres

**Performance Goals**: Schedule list load ≤1s p95 for ≤100 schedules per tenant; cron batch processes ≤500 due schedules per run in ≤30s; form next-date preview ≤100ms

**Constraints**:
- Service role key server-side only (cron + optional RPC)
- JPY fixed amounts only
- Max one occurrence per schedule per calendar day (idempotent)
- No backfill of missed runs while paused or down
- Recurrence depth L1/L2 only (aligned with 010 taxonomy)
- Category delete auto-pauses affected schedules (FR-020)

**Scale/Scope**: Household users; tens of schedules per tenant; hourly cron sufficient for timezone-aware daily evaluation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Shared `lib/periodic/` module; SQL in migrations; RPC for atomic cron batch |
| Test-First Delivery | Vitest recurrence matrix before UI; RPC idempotency tests; RLS cross-tenant deny tests |
| User Experience Consistency | ja/en/zh strings; mobile card list; drawer nav matches Categories pattern |
| Performance & Reliability | Indexed `(status, next_run_date)`; transactional occurrence insert; cron failure logs + retry next hour |
| Observability & Feedback | Structured logs on cron run (counts inserted/skipped/ended); no PII in client logs |

**Gate**: PASS

**Post-design re-check**: PASS — recurrence logic isolated and testable; writes scoped to new tables/RPC; existing bot path unchanged.

## Architecture

```text
┌──────────────────┐   drawer nav    ┌─────────────────────────────┐
│  /dashboard      │ ◄──────────────►│  /periodic-expenses         │
│  ExpenseList     │                 │  ScheduleCardList + Form    │
└────────┬─────────┘                 └──────────────┬──────────────┘
         │                                            │
         │  Supabase JS (read schedules via RLS)      │  /api/periodic-expenses/*
         ▼                                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Supabase Postgres                                                   │
│  periodic_expense_schedules (tenant-scoped, recurrence JSONB)        │
│  expenses (+ periodic_schedule_id, source_message_id idempotency)    │
│  RPC process_due_periodic_schedules(p_as_of timestamptz)           │
└──────────────────────────────────────────────────────────────────────┘
         ▲
         │ hourly Vercel Cron + CRON_SECRET
┌────────┴────────────────────────┐
│  GET /api/cron/process-periodic-expenses │
│  (service role → RPC)                    │
└──────────────────────────────────────────┘
```

### Create / edit flow

1. User opens `/periodic-expenses` with tenant from switcher.
2. Form loads categories via existing `/api/categories` (ensure tenant taxonomy).
3. User picks recurrence kind + params; client calls `computeNextRunDate` for preview.
4. `POST /api/periodic-expenses` validates, persists row, sets `next_run_date` from engine.

### Cron flow

1. Vercel Cron hits `/api/cron/process-periodic-expenses` with `Authorization: Bearer $CRON_SECRET`.
2. Route calls `process_due_periodic_schedules(now())` via service role.
3. RPC selects `status = 'active' AND next_run_date <= local_today(timezone)` for each schedule.
4. Per schedule (in transaction): check end conditions → insert expense → bump counters → compute next run or set `ended`.
5. Unique `(periodic_schedule_id, expense_date)` prevents duplicate same-day logging.

### Pause / category deleted

- Pause: `status = 'paused'`, keep `next_run_date` for display.
- Restart: recompute `next_run_date` from `max(today, start_date)` with current rules → `active`.
- Category deleted (010 hook): trigger or app logic sets `status = 'paused'`, `pause_reason = 'category_missing'`.

## Project Structure

### Documentation

```text
specs/011-periodic-expense-scheduler/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── supabase-schema-delta.md
    ├── periodic-expenses-api.md
    └── cron-processing.md
```

### Source Code

```text
supabase/migrations/
  20260623120000_periodic_expense_schedules.sql

web/
  vercel.json                              # add crons entry
  src/
    app/
      (app)/periodic-expenses/page.tsx
      api/periodic-expenses/
        route.ts                             # GET list, POST create
        [id]/route.ts                        # GET, PATCH
        [id]/pause/route.ts                  # POST pause
        [id]/restart/route.ts                # POST restart
      api/cron/process-periodic-expenses/route.ts
    components/
      SideDrawer.tsx                         # add navPeriodicExpenses
      periodic/
        ScheduleCard.tsx
        ScheduleCardList.tsx
        ScheduleForm.tsx                     # create/edit sheet
        RecurrenceFields.tsx
        EndConditionFields.tsx
    lib/periodic/
      types.ts
      recurrence.ts                          # pure date engine
      format.ts                              # human-readable labels (i18n keys)
      validation.ts
    lib/messages.ts                          # new i18n strings

web/tests/ or web/src/lib/periodic/__tests__/
  recurrence.test.ts
```

## Implementation Phases

### Phase 1 — Schema & recurrence engine (blocking)

1. Migration: `periodic_expense_schedules` table, indexes, RLS policies.
2. Migration: `expenses.periodic_schedule_id` FK + unique `(periodic_schedule_id, expense_date) WHERE periodic_schedule_id IS NOT NULL`.
3. RPC `process_due_periodic_schedules`.
4. Implement `lib/periodic/recurrence.ts` + Vitest matrix (all FR-003–007 cases).

### Phase 2 — Cron processor

1. `/api/cron/process-periodic-expenses` with `CRON_SECRET` guard.
2. `vercel.json` cron schedule (`0 * * * *` hourly UTC).
3. Env vars documented: `CRON_SECRET`, existing Supabase service role.
4. Integration test / manual curl verification.

### Phase 3 — API routes

1. CRUD + pause/restart endpoints with tenant validation.
2. Server-side next_run_date computation on create/edit/restart.
3. Ended schedule restart guard (require end-condition edit).

### Phase 4 — Web UI

1. Drawer nav link + `/periodic-expenses` page.
2. Card list (amount emphasized, status badges, next run).
3. Create/edit form with recurrence + end condition subforms.
4. Empty/loading/error states; i18n.

### Phase 5 — Category delete integration

1. On category delete (010 RPC), pause schedules referencing deleted node.
2. UI message on card when `pause_reason = 'category_missing'`.

### Phase 6 — Verification

1. Vitest recurrence + API validation tests.
2. SQL: RLS cross-tenant deny; RPC idempotency double-run same hour.
3. Manual: create schedule due today → trigger cron → expense in dashboard list.

## Risks & Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Recurrence edge-case bugs (month-end, leap year) | Exhaustive Vitest table; spec edge cases as test names |
| Cron misses hour during outage | Hourly schedule; `next_run_date <= local_today` catches up next hour (no duplicate same day) |
| Timezone drift | Store `timezone` per schedule; default `Asia/Tokyo`; evaluate with `AT TIME ZONE` in RPC |
| Group concurrent edits | Last-write-wins; recalc `next_run_date` on save |
| 009 read-only assumption broken | Scoped to new routes/table; expense inserts only via RPC/cron with synthetic `source_message_id` |

## Dependencies

- **009-expense-web-dashboard**: auth, tenant switcher, expense list — complete
- **010-tenant-category-editor**: tenant taxonomy, L1/L2 picker, side drawer — complete
- **006-group-expenses**: tenant columns on expenses — complete

## Suggested Next Command

After plan approval: `/speckit-tasks` to generate `tasks.md`.
