# Quickstart: Supabase Expense Storage

**Feature**: 004-supabase-expense-storage  
**Branch**: `004-supabase-expense-storage`

## Prerequisites

- Python 3.11+ with project dependencies installed (`pip install -r requirements.txt`)
- `GEMINI_API_KEY` (existing)
- Supabase project: **https://nyuenufldaqsjybjhawl.supabase.co**
- Service role key from Supabase Dashboard → Settings → API

## 1. Configure environment

Add to `.env`:

```env
GEMINI_API_KEY=your-gemini-key
SUPABASE_URL=https://nyuenufldaqsjybjhawl.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## 2. Apply database migration

After `/speckit-implement` creates `supabase/migrations/20260606120000_expense_schema.sql`:

**Option A — Supabase Dashboard**

1. Open SQL Editor for project `nyuenufldaqsjybjhawl`
2. Paste and run the migration SQL

**Option B — Supabase MCP** (after linking MCP to correct project)

Use `apply_migration` with the migration file contents.

**Verify**:

```sql
SELECT count(*) FROM category_nodes;  -- expect ~50+ seeded rows
SELECT count(*) FROM expenses;        -- expect 0
```

## 3. Log an expense via console

```bash
python local_run.py --text "スーパーで食料品 3500円"
```

Expected stdout (shape):

```text
Detected expense(s):
- 食料品: 3500.0 JPY
  Category (guess): 食費 > 食料品
  Please confirm or pick another:
  1) ...
```

## 4. Verify persistence

In Supabase SQL Editor:

```sql
SELECT description, amount, currency, expense_date, assigned_level
FROM expenses
ORDER BY created_at DESC
LIMIT 5;
```

## 5. Verify idempotency (after webhook wiring)

Re-send same LINE message ID in tests → row count unchanged.

Console reruns with new UUID → new rows (by design).

## 6. Run tests

```bash
pytest tests/test_expense_repository.py tests/test_categorize.py tests/test_message_handler_persistence.py -q
pytest -q   # full suite
```

## Rollup query examples (SQL)

After seeding expenses, verify monthly L1 food total (June 2026, JST calendar month on `expense_date`):

```sql
SELECT monthly_expense_total(
  'local-dev-user',
  2026,
  6,
  '249350c8-4b24-5117-a515-9ef3988701de',  -- food L1
  'JPY'
);
```

L2 dining rollup includes L3 cafe assignments but excludes L1-only food rows:

```sql
SELECT monthly_expense_total(
  'local-dev-user',
  2026,
  6,
  '02d581f8-33fd-514b-b6a7-47955de12b86',  -- food.dining L2
  'JPY'
);
```

Yearly total for transport L1:

```sql
SELECT yearly_expense_total(
  'local-dev-user',
  2026,
  '171920a3-e860-5c94-baf2-7b9bb2065a11',  -- transport L1
  'JPY'
);
```

Confirm budget placeholder table exists (no bot CRUD in v1):

```sql
SELECT count(*) FROM monthly_budgets;  -- expect 0
```

## Troubleshooting

| Issue | Check |
| ----- | ----- |
| No rows in `expenses` | `SUPABASE_*` set? Logs for "persistence skipped" |
| Wrong Supabase project | URL must be `nyuenufldaqsjybjhawl`, not MCP default |
| Reply without category block | Categorization service error — check Gemini logs |
| Duplicate rows on LINE retry | Unique constraint on `(line_user_id, source_message_id, line_item_index)` |

## MCP note

Supabase MCP server: **`project-0-linebot-money-tracker-supabase`**

Verified:
- Project URL: `https://nyuenufldaqsjybjhawl.supabase.co`
- Migration `expense_schema` applied via MCP during implement
- Tables: `category_nodes`, `expenses`, `monthly_budgets`, RPCs `monthly_expense_total` / `yearly_expense_total`

LLM returns JSON → app validates → `expense_repository.insert_expenses()` only. See [contracts/llm-db-boundary.md](./contracts/llm-db-boundary.md).
