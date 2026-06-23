# Data Model: Monthly Budget Manager

**Feature**: 012-monthly-budget-manager

## ERD (conceptual)

```text
category_nodes (tenant-scoped)
    │
    ├──< monthly_budgets >── tenant (type, id) + budget_month
    │
    └──< expenses >── tenant (type, id) + expense_date
                          │
                          └── (spent derived on read via cascade rules)
```

## Entity: monthly_budgets (evolved)

One row per configured limit at total, L1, or L2 for a tenant and fiscal month.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | `gen_random_uuid()` |
| tenant_type | text NOT NULL | `user` / `group` / `room` |
| tenant_id | text NOT NULL | LINE userId or chat ID |
| budget_level | text NOT NULL | `total` \| `l1` \| `l2` |
| category_node_id | uuid FK NULL → category_nodes | NULL when `budget_level = total` |
| budget_month | date NOT NULL | First day of fiscal month (JST calendar), e.g. `2026-06-01` |
| amount | numeric(14,2) NOT NULL | Limit amount; > 0 when row exists |
| currency | char(3) NOT NULL DEFAULT 'JPY' | MVP fixed JPY |
| created_at | timestamptz NOT NULL DEFAULT now() | |
| updated_at | timestamptz NOT NULL DEFAULT now() | |

**Constraints**:

- `amount > 0`
- `budget_level IN ('total', 'l1', 'l2')`
- Level ↔ category consistency (see Decision 2 in research.md)
- `category_node_id` must belong to same tenant when not null
- L1 node when `budget_level = l1`; L2 node when `budget_level = l2`

**Unique indexes**:

```sql
-- One total budget per tenant/month/currency
UNIQUE (tenant_type, tenant_id, budget_month, currency)
  WHERE budget_level = 'total';

-- One budget per category per month
UNIQUE (tenant_type, tenant_id, category_node_id, budget_month, currency)
  WHERE category_node_id IS NOT NULL;
```

**Indexes**:

- `(tenant_type, tenant_id, budget_month)` — summary fetch

**Absence of row** = unlimited at that level (FR-004).

### Migration from legacy schema

| Legacy | New |
| ------ | --- |
| `line_user_id` | `tenant_type = 'user'`, `tenant_id = line_user_id` |
| `category_node_id` (always set) | `budget_level` from `category_nodes.level`; no legacy total rows |

## Derived: budget bucket assignment (per expense)

Not persisted. Computed by `resolve_budget_bucket(expense, budgets_for_month)`:

| Step | Condition | Bucket |
| ---- | --------- | ------ |
| 1 | `assigned_level = 2` AND L2 budget for `category_node_id` | That L2 |
| 2 | L1 budget for `category_l1_id` | That L1 |
| 3 | Total budget row exists | `total` |
| 4 | Else | `unbudgeted` |

## Derived: spent amounts (per fiscal month)

| Meter | Spent formula |
| ----- | ------------- |
| **Total limit bar** | `SUM(amount)` of all non-deleted JPY expenses in month (when total limit set) |
| **L1 limit bar** | Sum of expenses whose bucket = that L1 node |
| **L2 limit bar** | Sum of expenses whose bucket = that L2 node |
| **L1 info row** (no L1 limit) | Sum of expenses under that L1 subtree (for breakdown UX) |
| **Unbudgeted callout** | Sum of expenses with bucket = `unbudgeted` |

Uses existing expense filters: `deleted_at IS NULL`, `currency = 'JPY'`, `tenant_type`/`tenant_id`, `expense_date` in month.

## Derived: budget health (per meter with limit)

| Field | Computation |
| ----- | ----------- |
| `limit` | `monthly_budgets.amount` or null |
| `spent` | Per table above |
| `remaining` | `max(limit - spent, 0)` when limit set |
| `spent_pct` | `spent / limit` |
| `time_pct` | `elapsed_days / days_in_month` (min elapsed = 1 on day 1) |
| `pace_ratio` | `spent_pct / time_pct` when `time_pct > 0` |
| `health` | `on_track` \| `caution` \| `over_pace` \| `neutral` |
| `pace_label_key` | i18n key for usability text |

## Entity: expenses (unchanged)

Budget feature **reads** expenses only. Relevant columns:

| Column | Budget use |
| ------ | ---------- |
| tenant_type, tenant_id | Scope |
| expense_date | Fiscal month membership |
| amount, currency | Spent |
| assigned_level | Cascade step 1 |
| category_node_id, category_l1_id, category_l2_id | Bucket resolution |
| deleted_at | Exclude when set |

Periodic auto-logged rows (011) included automatically.

## RPC: get_budget_summary

**Inputs**: `p_tenant_type`, `p_tenant_id`, `p_budget_month date`, `p_currency char(3) default 'JPY'`

**Returns** JSON:

```json
{
  "budget_month": "2026-06-01",
  "days_in_month": 30,
  "elapsed_days": 15,
  "total": { "limit": 100000, "spent": 70000, "remaining": 30000, "spent_pct": 0.7 },
  "categories": [
    {
      "node_id": "uuid",
      "level": 1,
      "name_ja": "食費",
      "limit": 50000,
      "spent": 20000,
      "suggested_from_children": 45000,
      "children": [
        {
          "node_id": "uuid",
          "level": 2,
          "name_ja": "外食",
          "limit": 20000,
          "spent": 15000,
          "suggested_from_history": 18000
        }
      ]
    }
  ],
  "unbudgeted_spent": 5000
}
```

- `suggested_from_children`: sum of child L2 limits (for L1 buffer UX)
- `suggested_from_history`: optional; may be filled by API not RPC

Access: `can_access_tenant` guard inside RPC (`SECURITY DEFINER`).

## RLS policies (new)

Mirror `periodic_expense_schedules` / `category_nodes` write pattern:

| Operation | Rule |
| --------- | ---- |
| SELECT | `can_access_tenant(tenant_type, tenant_id)` |
| INSERT | same |
| UPDATE | same |
| DELETE | same |

Enable authenticated policies; bot continues using service role (no budget CRUD).

## State transitions

```text
(no row) ──user sets amount──► active limit row
active limit row ──user clears/deletes──► (no row) unlimited
active limit row ──user edits amount──► active limit row (updated_at)
copy-from-previous ──► draft amounts in API response ──PUT──► new month rows
```

No runtime status field; presence of row = configured limit.

## Validation rules (API)

| Rule | Error |
| ---- | ----- |
| amount ≤ 0 | 400 |
| `budget_level = l2` but node is L1 | 400 |
| category from different tenant | 403/400 |
| duplicate total row for month | upsert |
| editing past months | read-only in v1 (current month only for PUT) |

## Suggested amounts (API-only, not stored)

| Source | Formula |
| ------ | ------- |
| L1 from children | `SUM(child L2 amounts)` in current edit draft |
| Total from L1 | `SUM(L1 amounts)` in current edit draft |
| History suggestion | `AVG(monthly_expense_total(...))` over prior 3 months where > 0 |
