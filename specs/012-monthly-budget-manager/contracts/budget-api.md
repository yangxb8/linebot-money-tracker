# Budget API Contract

**Feature**: 012-monthly-budget-manager

Base path: `/api/budgets`  
Auth: Supabase session required (same as dashboard).

## Common

**Tenant query params** (all routes):

| Param | Type | Description |
| ----- | ---- | ----------- |
| `tenant_type` | `user` \| `group` \| `room` | Ledger scope |
| `tenant_id` | string | LINE userId or chat ID |

**Month query param** (optional):

| Param | Type | Default |
| ----- | ---- | ------- |
| `budget_month` | `YYYY-MM-DD` (first of month) | Current month in JST |

Server validates caller has access via `can_access_tenant`.

---

## GET /api/budgets

Returns budget summary with limits, spent, tree breakdown, and fiscal month metadata.

**Query**: `tenant_type`, `tenant_id`, optional `budget_month`

**Response 200**:

```json
{
  "budget_month": "2026-06-01",
  "days_in_month": 30,
  "elapsed_days": 15,
  "currency": "JPY",
  "total": {
    "limit": 100000,
    "spent": 70000,
    "remaining": 30000,
    "spent_pct": 0.7,
    "has_limit": true
  },
  "categories": [
    {
      "node_id": "uuid",
      "code": "food",
      "name_ja": "食費",
      "level": 1,
      "limit": 50000,
      "spent": 20000,
      "spent_assigned": 5000,
      "spent_aggregate": 20000,
      "suggested_from_children": 45000,
      "has_limit": true,
      "children": [
        {
          "node_id": "uuid",
          "code": "food.dining",
          "name_ja": "外食",
          "level": 2,
          "limit": 20000,
          "spent": 15000,
          "has_limit": true
        }
      ]
    }
  ],
  "unbudgeted_spent": 5000,
  "has_any_limit": true
}
```

**Field notes**:

- `spent` on total = all month expenses (when `has_limit`)
- `spent_assigned` on L1/L2 = cascade-assigned amount only
- `spent_aggregate` on L1 = subtree total for informational rows
- `has_any_limit: false` → unlimited state (FR-004)
- When the requested month is the tenant's **current** fiscal period and has no budget rows, `get_budget_summary` lazy-copies from the previous fiscal period (if any) and may return `lazy_copied_from_previous: true`
- Health color computed client-side from `spent_pct` + `elapsed_days` / `days_in_month`

**Errors**: 400 invalid params, 401 unauthenticated, 403 forbidden tenant

---

## PUT /api/budgets

Upsert budget rows for the **current fiscal month only** (v1).

**Body**:

```json
{
  "tenant_type": "user",
  "tenant_id": "Uxxx",
  "budget_month": "2026-06-01",
  "currency": "JPY",
  "budgets": [
    { "budget_level": "total", "amount": 100000 },
    { "budget_level": "l1", "category_node_id": "uuid", "amount": 50000 },
    { "budget_level": "l2", "category_node_id": "uuid", "amount": 20000 }
  ],
  "clear_levels": [
    { "budget_level": "l2", "category_node_id": "uuid" }
  ]
}
```

- Omitted category rows = unchanged
- `clear_levels` removes limits (returns to unlimited)
- `amount` must be positive integer yen (no decimals in UI)

**Response 200**: same shape as `GET /api/budgets` after save.

**Errors**: 400 validation, 403 tenant, 409 category not in tenant tree

---

## POST /api/budgets/copy-from-previous

Returns draft budget amounts copied from prior fiscal month (user confirms via PUT).

**Body**:

```json
{
  "tenant_type": "user",
  "tenant_id": "Uxxx",
  "target_month": "2026-06-01"
}
```

**Response 200**:

```json
{
  "source_month": "2026-05-01",
  "budgets": [
    { "budget_level": "total", "amount": 100000 },
    { "budget_level": "l1", "category_node_id": "uuid", "amount": 50000 }
  ],
  "available": true
}
```

When no prior month budgets: `{ "available": false, "budgets": [] }`

---

## GET /api/budgets/suggestions

3-month average spend per category for setup helpers.

**Query**: `tenant_type`, `tenant_id`, optional `category_node_id` (if omitted, all L1/L2 nodes)

**Response 200**:

```json
{
  "suggestions": [
    {
      "category_node_id": "uuid",
      "level": 2,
      "average_monthly_spent": 18500,
      "months_sampled": 3
    }
  ]
}
```

- Uses `monthly_expense_total` for each of the 3 months before `budget_month`
- `months_sampled` may be < 3 when history is short

---

## Client-only: health computation

Not an API route. `web/src/lib/budget/health.ts`:

```typescript
type HealthInput = {
  spent: number;
  limit: number | null;
  elapsedDays: number;
  daysInMonth: number;
};

type HealthResult = {
  spentPct: number | null;
  timePct: number;
  paceRatio: number | null;
  tone: "neutral" | "good" | "caution" | "bad";
  labelKey: string;
};
```

---

## Error envelope

```json
{ "error": "Human-readable message" }
```

Status codes: 400, 401, 403, 500
