# Data Model: Budget Pace Alert in LINE Bot Replies

**Feature**: 015-budget-pace-alert

## Overview

No new persisted tables. This feature adds **derived runtime objects** built from existing `monthly_budgets`, `expenses`, `category_nodes`, and `get_budget_summary` RPC output.

## Existing entities (read-only for this feature)

### monthly_budgets

Configured limits per tenant, fiscal month, and level (`total` | `l1` | `l2`). Absence of row = unlimited at that level.

### expenses

Source of spent totals via RPC aggregation. Relevant fields after persist/edit:

| Field | Use |
| ----- | --- |
| `tenant_type`, `tenant_id` | Ledger scope (personal vs group) |
| `expense_date` | Fiscal month for summary RPC |
| `amount`, `currency` | Spending (JPY only) |
| `assigned_level` | 1 or 2 — determines which cascade levels to evaluate |
| `category_node_id` | L2 node when `assigned_level = 2` |
| `category_l1_id` | Parent L1 for cascade |
| `deleted_at` | Excluded from spent |

### category_nodes

Provides display names for warned buckets (`name_ja`, `code`).

## Derived: BudgetLevelCandidate

One evaluatable budget level for a single expense path.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `level` | `l2` \| `l1` \| `total` | Cascade level |
| `category_node_id` | uuid \| null | null for total |
| `limit` | decimal | Budget cap from `monthly_budgets` |
| `spent` | decimal | From `spent_by_bucket[level:uuid]` or `total` |
| `remaining` | decimal | `max(limit - spent, 0)` for display |
| `display_name` | string | Localized category label or "総予算" / "Total budget" |

**Collection rule** (FR-003):

| Expense `assigned_level` | Candidates (only if budget row exists) |
| ------------------------ | -------------------------------------- |
| 2 (L2/L3 leaf) | L2 for `category_node_id` → L1 for `category_l1_id` → total |
| 1 | L1 for `category_node_id` → total |

Order preserved: most specific first.

## Derived: PaceEvaluation

Result of health math for one candidate.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `candidate` | BudgetLevelCandidate | Level under test |
| `elapsed_days` | int | From RPC |
| `days_in_month` | int | From RPC |
| `days_remaining` | int | `max(days_in_month - elapsed_days, 0)` |
| `pace_ratio` | float \| null | null = neutral (day 1 / no limit) |
| `is_ahead` | bool | `pace_ratio is not None and pace_ratio > 1` |
| `daily_allowance` | int | `floor(remaining / days_remaining)` when `days_remaining > 0`, else 0 |

## Derived: PaceWarning

Message block prepended to bot reply.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `level` | `l2` \| `l1` \| `total` | Lowest ahead level (FR-003b) |
| `display_name` | string | Category or total label |
| `daily_allowance` | int | Recommended ¥/day |
| `remaining` | decimal | Budget remaining |
| `text` | string | Final localized warning with emoji |
| `source` | `llm` \| `template` | How `text` was produced |

## Flow: resolve lowest ahead warning

```text
For each distinct expense path in the action:
  1. Load get_budget_summary(tenant, budget_month from expense_date)
  2. Build ordered BudgetLevelCandidate list (L2 → L1 → total, skip undefined)
  3. For each candidate in order:
       compute PaceEvaluation
       if is_ahead: return PaceWarning for this candidate; STOP
  4. No warning for this path

Combine warnings for multiple paths into one prepended block (blank line before confirmation)
```

## State transitions

Not applicable — no persisted pace-warning state. Each confirmation/reply-edit evaluates fresh from DB.

## Validation rules

- Skip pace check when Supabase not configured (local dev without keys).
- Skip when `has_any_limit` is false in RPC response.
- Skip when `days_remaining == 0` (month ended).
- `daily_allowance` uses `floor` (match web `BudgetRow.tsx`).
- Exhausted budget (`remaining == 0`): daily allowance 0 with exhausted messaging.
