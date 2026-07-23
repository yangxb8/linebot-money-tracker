# Budget Pace Evaluation Contract

**Feature**: 015-budget-pace-alert  
**Type**: Internal Python service contract (bot)

## Module

`services/budget_pace.py`

## Public functions

### `fetch_budget_summary(tenant, budget_month, currency='JPY') -> dict | None`

Calls Supabase RPC `get_budget_summary`. Returns parsed JSON or `None` on failure / unconfigured Supabase.

**Inputs**:

| Param | Type | Notes |
| ----- | ---- | ----- |
| `tenant` | `TenantContext` | `tenant_type`, `tenant_id` |
| `budget_month` | `date` | First day of fiscal month for expense |
| `currency` | `str` | Default `JPY` |

**Output** (subset used):

```python
{
    "budget_month": "2026-06-01",
    "days_in_month": 30,
    "elapsed_days": 10,
    "currency": "JPY",
    "has_any_limit": True,
    "budgets": [
        {"budget_level": "l2", "category_node_id": "uuid", "amount": 30000},
        {"budget_level": "l1", "category_node_id": "uuid", "amount": 50000},
        {"budget_level": "total", "category_node_id": None, "amount": 100000},
    ],
    "spent_by_bucket": {
        "l2:uuid": 25000,
        "l1:uuid": 40000,
        "total": 70000,
    },
}
```

---

### `compute_budget_health(spent, limit, elapsed_days, days_in_month) -> HealthResult`

Mirrors `web/src/lib/budget/health.ts`.

| Field | Type |
| ----- | ---- |
| `pace_ratio` | `float \| None` |
| `is_ahead` | `bool` — `pace_ratio is not None and pace_ratio > 1` |

---

### `build_level_candidates(expense_row, budgets) -> list[BudgetLevelCandidate]`

Builds ordered candidates per data-model rules. Omits levels without configured limits.

**Input expense_row**:

```python
{
    "assigned_level": 2,
    "category_node_id": "uuid",
    "category_l1_id": "uuid",
    "expense_date": "2026-06-10",
}
```

---

### `find_lowest_ahead_warning(candidates, summary, category_names) -> PaceWarning | None`

Evaluates candidates in order (L2 → L1 → total). Returns first ahead-of-pace warning or `None`.

---

### `evaluate_pace_warnings(expense_rows, tenant) -> list[PaceWarning]`

Top-level entry: one RPC call per distinct `(tenant, budget_month)` batch; dedupe paths; return 0..N warnings.

## Pace definition

```text
time_pct = max(elapsed_days, 1) / days_in_month   (clamped 0..1; min 1-day floor)
spent_pct = spent / limit
pace_ratio = spent_pct / time_pct         (when elapsed_days > 0 and limit > 0)
is_ahead = pace_ratio > 1
```

Day 1 uses a **minimum 1-day time denominator** so front-loaded spend (rent, periodic expenses on fiscal start) can still be ahead of pace. Neutral only when `elapsed_days <= 0` or there is no limit.

## Lowest-level selection examples

| L2 ahead | L1 ahead | Total ahead | Warning level |
| -------- | -------- | ----------- | ------------- |
| yes | yes | yes | L2 |
| no | yes | yes | L1 |
| no | no | yes | total |
| no | no | no | none |

## Error handling

| Condition | Behavior |
| --------- | -------- |
| RPC failure | Return `[]`; log warning |
| Supabase not configured | Return `[]` |
| No limits configured | Return `[]` |
| Category name lookup fails | Use `code` fallback |
