# Research: Monthly Budget Manager

**Feature**: 012-monthly-budget-manager

## Decision 1: Evolve existing `monthly_budgets` table (tenant-scoped)

**Decision**: **Migrate** the placeholder `monthly_budgets` table to add `tenant_type`, `tenant_id`, `budget_level` (`total` | `l1` | `l2`), nullable `category_node_id` (NULL for total), and `updated_at`. Drop legacy `line_user_id`.

**Rationale**: Table already exists from feature 004 with RLS enabled but no policies. Avoids a rename migration and keeps budget data colocated with the original schema intent.

**Alternatives considered**:
- **New `tenant_monthly_budgets` table** — duplicates naming; requires dropping old table anyway.
- **JSONB blob per tenant/month** — harder to query, no FK to category_nodes, weak RLS granularity.

## Decision 2: Total budget row shape

**Decision**: One row with `budget_level = 'total'` and `category_node_id IS NULL` per `(tenant, budget_month, currency)`.

**Rationale**: Spec requires optional overall cap distinct from category rows. Nullable FK with level check is clearer than a sentinel UUID.

**Constraint sketch**:

```sql
CHECK (
  (budget_level = 'total' AND category_node_id IS NULL)
  OR (budget_level IN ('l1','l2') AND category_node_id IS NOT NULL)
)
```

## Decision 3: Spent figures are computed on read (not materialized)

**Decision**: No `budget_spent` columns or bot-side budget hooks. **`get_budget_summary` RPC** (and shared TS `resolveBudgetBucket`) derive spent from `expenses` at request time.

**Rationale**: FR-008 requires recalculation on expense amount/category/date/delete changes. Materialized counters would need triggers on every expense write path (bot, cron, reply-edit). On-read aggregation is correct by construction and matches household scale (hundreds of rows/month).

**Alternatives considered**:
- **Expense triggers updating counters** — fragile across bot + web + cron writers; easy to drift.
- **Nightly batch recompute** — violates SC-001/SC-003 latency expectations.

## Decision 4: Cascade assignment (one bucket per expense)

**Decision**: Each expense maps to **at most one** budget bucket per month using this order:

1. **L2 bucket** — expense `assigned_level = 2` and an L2 budget exists for `category_node_id`
2. **L1 bucket** — an L1 budget exists for `category_l1_id`
3. **Total bucket** — a total budget row exists for the month
4. **Unbudgeted** — no bucket; expense still visible in spending totals but not in any limit meter

**Rationale**: Matches FR-007 and edge case "each level tracks independently." L1/L2 meters reflect only expenses that resolved to that level, not double-counted descendants.

**Display overlay for total cap**: When a **total** budget limit is configured, the **total progress bar spent** = **sum of all** non-deleted JPY expenses in the month (overall monthly cap semantics per User Story 1). L1/L2 meters still use cascade-assigned amounts only.

**Alternatives considered**:
- **Hierarchical rollup** (L2 spend also increments L1 and total meters) — conflicts with independent-level edge cases in spec.
- **Total meter = only unallocated cascade** — confusing when user sets total + category budgets expecting an overall cap.

## Decision 5: Reuse `monthly_expense_total` for suggestions

**Decision**: **3-month average suggestions** call existing RPC `monthly_expense_total(tenant, year, month, category_node_id, 'JPY')` per category for prior months; average in API layer.

**Rationale**: RPC already implements L1/L2 rollup semantics aligned with tenant expenses post–010 taxonomy. No new SQL for historical spend.

## Decision 6: Web API surface

**Decision**: Next.js route handlers at **`/api/budgets/*`** mirroring 010/011 patterns (`tenant_type`, `tenant_id` query params, session auth, `can_access_tenant`).

| Route | Purpose |
| ----- | ------- |
| `GET /api/budgets` | Summary for month (limits, spent, health inputs, suggestions metadata) |
| `PUT /api/budgets` | Upsert batch of budget rows for current month |
| `POST /api/budgets/copy-from-previous` | Pre-fill from prior month (returns draft, user confirms via PUT) |
| `GET /api/budgets/suggestions` | 3-month average per category node |

**Rationale**: Server validates level/category consistency, enforces tenant access, shapes tree for UI. Matches established dashboard write pattern.

## Decision 7: Health color computation (client-side)

**Decision**: Pure function in **`web/src/lib/budget/health.ts`**:

- `timePct` = elapsed days in fiscal month / total days (min denominator 1 on day 1 → neutral)
- `spentPct` = spent / limit (when limit set)
- `paceRatio` = spentPct / timePct (when both > 0)
- Map ratio to green → yellow → red gradient; attach i18n pace label

**Rationale**: Presentation logic; no persistence. Unit-testable without DB. Spec usability enhancements (pace label, daily allowance) computed alongside.

## Decision 8: No bot changes in v1

**Decision**: Bot does not read or write budgets. Expense ingestion paths unchanged; budget view reflects them via shared `expenses` table.

**Rationale**: Spec out of scope: "Budget management from the LINE bot." On-read spent satisfies FR-007–009 without coupling bot deploy to budget feature.

## Decision 9: Category delete / move

**Decision**: **No budget-row migration** on category delete. Budget rows referencing deleted `category_node_id` become orphaned; API filters them out and UI shows warning to clear. Optional follow-up: pause-style flag on delete (deferred — low volume).

**Rationale**: 010 delete requires expense transfer first; budgets are limits not expense anchors. Simpler than cascading budget merges.

## Decision 10: Fiscal month identification

**Decision**: `budget_month` column stores **first calendar day** of month in JST (`date`, e.g. `2026-06-01`). Expense membership uses `expense_date` year/month in JST (same as existing RPCs).

**Rationale**: Matches legacy `monthly_budgets.budget_month` convention from 004. Custom fiscal start deferred per spec.
