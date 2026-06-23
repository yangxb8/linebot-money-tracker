# Research: Periodic Expense Scheduler

**Feature**: 011-periodic-expense-scheduler

## Decision 1: Where scheduled execution runs

**Decision**: **Vercel Cron** → Next.js **`/api/cron/process-periodic-expenses`** → Supabase RPC **`process_due_periodic_schedules`** with **service role**.

**Rationale**: The web app already deploys on Vercel (009). Cron is native, requires no new infrastructure, and keeps expense-insert logic next to the recurrence TypeScript module. RPC wraps inserts in a transaction with row-level locking for idempotency.

**Alternatives considered**:
- **Supabase pg_cron + Edge Function** — adds platform surface; duplicates insert logic in Deno.
- **Bot-side daily job on Cloud Run** — couples scheduling to bot deploy; web feature should not require bot changes.
- **Client-triggered execution** — unreliable; fails when user offline.

## Decision 2: Cron frequency

**Decision**: **Hourly** (`0 * * * *` UTC) with per-schedule **timezone** column (default `Asia/Tokyo`).

**Rationale**: FR-010 requires evaluation in the creator's timezone. A single daily UTC run mis-fires for non-JST users. Hourly scan with `next_run_date <= (now() AT TIME ZONE schedule.timezone)::date` is simple and sufficient at household scale.

**Alternatives considered**:
- **Once daily at 00:05 JST** — acceptable MVP per spec assumption but blocks future timezones.
- **Per-minute** — unnecessary for date-granular schedules.

## Decision 3: Recurrence representation

**Decision**: **JSONB `recurrence` column** with discriminated `kind` + params; pure functions in **`web/src/lib/periodic/recurrence.ts`**.

**Rationale**: Five rule kinds share next-date computation but differ in params. JSONB avoids sparse columns; TypeScript engine is unit-testable and reused by form preview and server validation. Same module imported by cron route for post-insert next-date (RPC can delegate or duplicate minimal SQL — prefer TS in API layer calling RPC with precomputed next date).

**Schema sketch**:

```json
{ "kind": "interval_days", "interval": 20 }
{ "kind": "monthly_days", "days": [1, 15] }
{ "kind": "monthly_boundary", "boundary": "first" | "last" }
{ "kind": "every_n_months", "interval": 3, "day": 10 }
{ "kind": "every_n_weeks", "interval": 3, "weekdays": [3] }
```

**Alternatives considered**:
- **iCal RRULE strings** — over-flexible, harder to validate in UI.
- **Separate columns per kind** — wide table, awkward queries.

## Decision 4: Idempotency for auto-logged expenses

**Decision**: Add **`expenses.periodic_schedule_id`** (nullable FK) + **unique index** on `(periodic_schedule_id, expense_date)` where not null. Synthetic **`source_message_id`**: `periodic:{schedule_uuid}:{YYYY-MM-DD}`.

**Rationale**: Reuses existing expense uniqueness `(tenant_type, tenant_id, source_message_id, line_item_index)` for upsert safety. Schedule FK enables occurrence counting and amount-cap end conditions without scanning descriptions.

**Alternatives considered**:
- **Separate `periodic_occurrences` table only** — still need expense row for dashboard; dual write complexity.
- **Count-only on schedule without FK** — loses audit trail per occurrence.

## Decision 5: End condition storage

**Decision**: Columns on schedule row: `end_kind` (`never` | `on_date` | `amount_cap` | `repeat_count`), nullable `end_date`, `end_amount_cap`, `end_repeat_limit`; runtime counters `occurrence_count`, `cumulative_amount`.

**Rationale**: Fixed set of end types; counters updated atomically in RPC. Amount cap checked before insert: `cumulative_amount + amount > cap` → end without partial occurrence.

## Decision 6: Write API surface

**Decision**: Next.js **Route Handlers** at `/api/periodic-expenses/*` (same pattern as 010 categories).

**Rationale**: Server validates recurrence JSON, recomputes `next_run_date`, enforces ended-state restart rules. Browser uses authenticated Supabase client for **read list** optional — MVP uses API for all writes and list for consistent shaping + category name joins.

**Alternatives considered**:
- **Direct Supabase client writes** — recurrence validation duplicated client/server; harder to test.
- **Supabase Edge Functions** — deferred per 009.

## Decision 7: Timezone source

**Decision**: Store **`timezone`** on schedule at create time; default **`Asia/Tokyo`**. Future: copy from user preference row when added.

**Rationale**: Spec defaults JST; decouples cron from joining `user_language_preferences`. Edit does not retroactively shift past occurrences.

## Decision 8: Category delete behavior

**Decision**: **Database trigger** on `category_nodes` DELETE (tenant rows) sets matching schedules to `paused` with `pause_reason = 'category_missing'`.

**Rationale**: FR-020 must hold even if delete happens via RPC while no user is on Periodic Expenses page. Trigger is reliable; UI reads `pause_reason` for message.

## Decision 9: Card list UX

**Decision**: Vertical **card stack** on mobile; amount as **large bold** primary text; secondary row for frequency + category; badge for paused/ended; footer for next run date.

**Rationale**: Matches spec emphasis on scannable amount; consistent with ExpenseList mobile density.

## Decision 10: Ended schedule restart

**Decision**: **Restart API returns 409** unless body includes updated `end_kind` / limits (user must explicitly extend end date, raise cap, or increase repeat limit).

**Rationale**: Spec FR-013 / user story 4 scenario 5 — prevent silent resume of exhausted schedules.

## Open questions (deferred)

- User-configurable occurrence time-of-day — out of scope (date-only batch).
- LINE notification on auto-log — out of scope.
- Bulk import of schedules — not requested.
