# Data Model: Monthly Expense Report

**Feature**: 022-monthly-expense-report

## ERD (conceptual)

```text
tenant (type, id)
    │
    ├──< monthly_report_artifacts >── (period_start)
    │         │
    │         └── Storage object (PNG)
    │
    └──< monthly_report_tips >── (tip_period_start)

Reads (no ownership):
    expenses, monthly_budgets, category_nodes, tenant_settings.fiscal_start_day
```

## Entity: monthly_report_artifacts

Prepared report for one ledger fiscal period.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | `gen_random_uuid()` |
| tenant_type | text NOT NULL | `user` / `group` / `room` |
| tenant_id | text NOT NULL | LINE userId or chat ID |
| period_start | date NOT NULL | Fiscal period start (aligned with budget month key) |
| period_end | date NOT NULL | Inclusive end day of fiscal period |
| status | text NOT NULL | `preparing` \| `ready` \| `failed` |
| data_fingerprint | text NOT NULL | Hash of period expenses + budgets (+ fiscal_start_day) used for invalidate/refresh |
| style_fingerprint | text NOT NULL | Hash of persona / reply language / emoji level / custom style inputs |
| storage_path | text NULL | Object path in `monthly-reports` bucket when ready |
| insight_text | text NULL | On-image commentary (also usable as caption seed) |
| snapshot_json | jsonb NULL | Budget comparison snapshot used for chart (total + worst-variance cats) |
| error_code | text NULL | Stable code when `failed` |
| prepared_at | timestamptz NULL | When status became `ready` |
| created_at | timestamptz NOT NULL DEFAULT now() | |
| updated_at | timestamptz NOT NULL DEFAULT now() | |

**Constraints**:
- `status IN ('preparing', 'ready', 'failed')`
- Unique `(tenant_type, tenant_id, period_start)` — one artifact row per ledger/period (upsert/replace on refresh)
- When `status = 'ready'`, `storage_path` and `snapshot_json` MUST be present
- When `status = 'failed'`, `error_code` SHOULD be set; `storage_path` NULL

**Indexes**:
- Unique `(tenant_type, tenant_id, period_start)`
- `(tenant_type, tenant_id, status, updated_at DESC)` for operational queries

## Entity: monthly_report_tips

Tracks that the new-period availability tip was shown for a conversation/period.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | |
| tenant_type | text NOT NULL | Conversation ledger (`user` / `group` / `room`) |
| tenant_id | text NOT NULL | |
| tip_period_start | date NOT NULL | Fiscal period start **of the new period** in which the tip was shown (i.e. current period after rollover) |
| shown_at | timestamptz NOT NULL DEFAULT now() | |

**Constraints**:
- Unique `(tenant_type, tenant_id, tip_period_start)` — enforces once per conversation per new period (group = once for whole group chat)

## Derived: Report Period

Not stored as its own table; computed from `fiscal_start_day` + as-of date (JST):

| Concept | Definition |
| ------- | ---------- |
| Current period | Fiscal span containing today |
| Previous completed | Fiscal span immediately before current |
| Named past/current | Mapped to fiscal `period_start` via user phrasing |

## Derived: Budget Comparison Snapshot (`snapshot_json`)

| Field | Notes |
| ----- | ----- |
| total | `{ limit, spent, remaining, pace_ratio? }` or null if no total budget |
| categories | Array (≤3) of `{ category_node_id, name, level, limit, spent, remaining, pace_ratio?, variance_rank }` |
| has_any_budget | bool |
| top_spend_category | `{ id, name }` for theme accent (deterministic tie-break) |
| overspend_severity | `none` \| `caution` \| `high` from total/category overshoot and pace |

## State transitions (artifact)

```text
(missing) → preparing   # first ask or refresh
preparing → ready       # PNG uploaded + snapshot saved
preparing → failed      # prepare error
ready → preparing       # fingerprint mismatch on next ask (refresh)
failed → preparing      # retry on next ask
```

## Access

- Bot uses **service role** (same as expenses/confirmations).
- No end-user RLS for Storage objects; URLs are short-lived signed links for LINE fetch only.
- Web dashboard does not read these tables in v1.
