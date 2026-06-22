# Data Model: Periodic Expense Scheduler

**Feature**: 011-periodic-expense-scheduler

## ERD (conceptual)

```text
category_nodes (tenant-scoped)
    │
    ├──< periodic_expense_schedules >── tenant (type, id)
    │         │
    │         └──< expenses (periodic_schedule_id optional)
    │
tenant_chat_members (group/room access)
line_auth_identities (creator attribution)
```

## Entity: periodic_expense_schedules

One row per user-defined recurring expense rule.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | `gen_random_uuid()` |
| tenant_type | text NOT NULL | `user` / `group` / `room` |
| tenant_id | text NOT NULL | LINE userId or chat ID |
| name | text NOT NULL | Display + expense description |
| amount | numeric(14,2) NOT NULL | Fixed JPY per occurrence; > 0 |
| currency | char(3) NOT NULL DEFAULT 'JPY' | MVP fixed JPY |
| assigned_level | smallint NOT NULL | 1 or 2 |
| category_node_id | uuid FK → category_nodes NOT NULL | Deepest assigned node |
| category_l1_id | uuid FK NOT NULL | Denormalized |
| category_l2_id | uuid FK NULL | Set when assigned_level = 2 |
| recurrence | jsonb NOT NULL | See recurrence kinds below |
| start_date | date NOT NULL | First eligible occurrence anchor |
| timezone | text NOT NULL DEFAULT 'Asia/Tokyo' | IANA tz for daily evaluation |
| end_kind | text NOT NULL | `never` \| `on_date` \| `amount_cap` \| `repeat_count` |
| end_date | date NULL | Required when `end_kind = on_date` |
| end_amount_cap | numeric(14,2) NULL | Required when `end_kind = amount_cap` |
| end_repeat_limit | int NULL | Required when `end_kind = repeat_count` |
| status | text NOT NULL | `active` \| `paused` \| `ended` |
| pause_reason | text NULL | e.g. `category_missing`, `user` |
| next_run_date | date NULL | Next scheduled occurrence (local calendar date in `timezone`) |
| occurrence_count | int NOT NULL DEFAULT 0 | Successful logged occurrences |
| cumulative_amount | numeric(14,2) NOT NULL DEFAULT 0 | Sum of logged amounts |
| created_by_line_user_id | text NOT NULL | Attribution for auto-logged expenses |
| created_at | timestamptz NOT NULL DEFAULT now() | |
| updated_at | timestamptz NOT NULL DEFAULT now() | |

**Constraints**:

- `amount > 0`
- `assigned_level IN (1, 2)`
- `status IN ('active', 'paused', 'ended')`
- `end_kind` check matches nullable end columns populated
- `recurrence` validated by app against allowed JSON schema

**Indexes**:

- `(tenant_type, tenant_id, status, next_run_date)` — list + cron scan
- `(status, next_run_date)` WHERE `status = 'active'` — cron partial index

## Recurrence JSON shapes

| kind | JSON | Params |
| ---- | ---- | ------ |
| `interval_days` | `{ "kind": "interval_days", "interval": N }` | N ≥ 1 |
| `monthly_days` | `{ "kind": "monthly_days", "days": [1,15,31] }` | days 1–31, sorted unique |
| `monthly_boundary` | `{ "kind": "monthly_boundary", "boundary": "first" \| "last" }` | |
| `every_n_months` | `{ "kind": "every_n_months", "interval": N, "day": D }` | N ≥ 1, D 1–31 |
| `every_n_weeks` | `{ "kind": "every_n_weeks", "interval": N, "weekdays": [0-6] }` | N ≥ 1; 0=Sun … 6=Sat |

## Entity: expenses (extended)

| Column | Type | Notes |
| ------ | ---- | ----- |
| periodic_schedule_id | uuid FK NULL → periodic_expense_schedules | Set for auto-logged rows |

**New unique index**:

```sql
CREATE UNIQUE INDEX expenses_periodic_occurrence_uq
  ON expenses (periodic_schedule_id, expense_date)
  WHERE periodic_schedule_id IS NOT NULL AND deleted_at IS NULL;
```

**Synthetic source for cron inserts**:

| Field | Value |
| ----- | ----- |
| source_message_id | `periodic:{schedule_id}:{expense_date}` |
| line_item_index | 0 |
| logged_by_line_user_id | `created_by_line_user_id` from schedule |
| line_user_id | same as logged_by (personal) or schedule creator for group attribution |
| description | schedule.name |

## State transitions

```text
                    create
                      │
                      ▼
                   [active] ──pause──► [paused]
                      │                    │
           end cond met│                    │ restart (+ optional end edit)
                      ▼                    │
                   [ended] ◄─── cannot restart without end edit
                      │
                      └── edit end + restart ──► [active]
```

| From | Event | To | Side effects |
| ---- | ----- | -- | ------------ |
| — | create | active | set `next_run_date` from engine |
| active | pause (user) | paused | `pause_reason = 'user'` |
| active | end condition met | ended | `next_run_date = NULL` |
| active | category deleted | paused | `pause_reason = 'category_missing'` |
| paused | restart | active | recompute `next_run_date` from today |
| paused/ended | delete schedule | (row removed) | expenses retained |
| ended | restart without end edit | — | 409 rejected |
| ended | restart with end edit | active | reset counters optional policy: keep counters |

**Counter policy on restart from ended**: Keep `occurrence_count` and `cumulative_amount` unless user resets end condition in a way that implies new lifecycle (document: raising cap above cumulative allows resume without reset).

## RPC: process_due_periodic_schedules

**Input**: `p_as_of timestamptz DEFAULT now()`

**Logic** (per schedule, serializable or `FOR UPDATE SKIP LOCKED`):

1. Select active schedules where `next_run_date <= (p_as_of AT TIME ZONE timezone)::date`.
2. For each:
   - If `end_kind = on_date` and `next_run_date > end_date`: mark ended, continue.
   - If `end_kind = repeat_count` and `occurrence_count >= end_repeat_limit`: mark ended, continue.
   - If `end_kind = amount_cap` and `cumulative_amount + amount > end_amount_cap`: mark ended, continue.
   - Insert expense (idempotent via unique index).
   - Increment counters; compute next `next_run_date` via app-provided function or inline SQL helper.
   - If no future occurrence or end now met: `status = ended`, `next_run_date = NULL`.

**Output**: `{ processed: N, inserted: N, ended: N, skipped: N }`

## RLS: periodic_expense_schedules

| Operation | Personal (`user`) | Group/Room |
| --------- | ----------------- | ---------- |
| SELECT | `tenant_id = current_line_user_id()` | member via `tenant_chat_members` |
| INSERT | owner | member |
| UPDATE | owner | member |
| DELETE | owner | member |

Cron RPC uses **service role** (bypasses RLS).

## Trigger: pause schedules on category delete

On `DELETE` from `category_nodes` WHERE `tenant_type IS NOT NULL`:

```sql
UPDATE periodic_expense_schedules
SET status = 'paused', pause_reason = 'category_missing', updated_at = now()
WHERE status = 'active'
  AND tenant_type = OLD.tenant_type
  AND tenant_id = OLD.tenant_id
  AND (category_node_id = OLD.id OR category_l1_id = OLD.id OR category_l2_id = OLD.id);
```

## View: v_periodic_schedules_enriched (optional)

Join schedules → category_nodes for L1/L2 names used in cards. Can be app-side join in API instead.

## Application state: Periodic Expenses page

| State | Description |
| ----- | ----------- |
| loading | Fetching schedules for tenant |
| ready | Card list displayed |
| form_open | Create/edit sheet visible |
| empty | No schedules; CTA to create |
| error | Fetch or save failure |

## Recurrence engine API (TypeScript)

```typescript
computeNextRunDate(
  recurrence: RecurrenceRule,
  anchor: Date,           // start_date or last occurrence
  after: Date,            // find strictly after this local date (for restart)
  timezone: string,
): Date | null

formatRecurrenceSummary(recurrence: RecurrenceRule, locale: string): string
```

## Indexes summary

- `periodic_expense_schedules(tenant_type, tenant_id)`
- `periodic_expense_schedules(status, next_run_date) WHERE status = 'active'`
- `expenses(periodic_schedule_id, expense_date)` unique partial
