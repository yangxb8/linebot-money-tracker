# Quickstart: Monthly Budget Manager

**Feature**: 012-monthly-budget-manager

## Prerequisites

- Features **009**, **010**, and **011** complete (auth, tenant switcher, categories, periodic expenses)
- Supabase env in `web/.env.local`: `NEXT_PUBLIC_SUPABASE_URL`, anon key, `SUPABASE_SERVICE_ROLE_KEY`
- LINE Login / LIFF working per `specs/009-expense-web-dashboard/quickstart.md`

## Apply migration

```bash
# From repo root
supabase db push
# Or run manually:
# supabase/migrations/20260624120000_monthly_budgets_tenant.sql
```

Verify:

```sql
\d monthly_budgets
SELECT policyname FROM pg_policies WHERE tablename = 'monthly_budgets';
SELECT proname FROM pg_proc WHERE proname IN ('get_budget_summary', 'resolve_budget_bucket');
```

## Run web app

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000/budget` (after LINE sign-in).

## Manual test flow

### 1. Unlimited default

1. Sign in, select personal ledger.
2. Open **Budget** from side drawer.
3. Confirm empty/unlimited state with current-month spending total and no red/green pressure.

### 2. Set total budget

1. Enter ¥50,000 total budget, save.
2. Log expenses via bot: `python local_run.py --text "ランチ 1200円"`
3. Refresh budget page — total spent increases, progress bar updates.

### 3. L2 cascade

1. Set L2 budget for **外食** ¥10,000 only (no total).
2. Log expense categorized to **外食** L2.
3. Confirm L2 meter increments; unrelated categories do not.

### 4. Health color

1. Set total ¥50,000 early in month.
2. Log expenses totaling > 50% of budget in first week.
3. Confirm health indicator shifts toward red (pace label visible).

### 5. Category edit recalc

1. Note L2 **外食** spent amount.
2. Reply-edit expense to **食料品**:  
   `python local_run.py --reply-to <bot_message_id> --text "食料品"`
3. Refresh budget — **外食** decreases, **食料品** increases (if budgeted).

### 6. Group ledger

```bash
python local_run.py --group-id <group_id> --text "会議弁当 800円"
```

1. Switch tenant to group in dashboard.
2. Set group budget, confirm group expenses count (not personal).

### 7. Copy from previous month

1. Set budgets in current month, wait or manually insert prior month rows in SQL.
2. Tap **Copy from last month**, confirm pre-fill, save.

### 8. Suggestions

1. Ensure 3 months of history for a category.
2. Tap suggest on L2 row — average appears.

## API smoke tests

```bash
# Replace SESSION_COOKIE and tenant params
curl -s "http://localhost:3000/api/budgets?tenant_type=user&tenant_id=Uxxx" \
  -H "Cookie: ..."

curl -s -X PUT "http://localhost:3000/api/budgets" \
  -H "Content-Type: application/json" \
  -H "Cookie: ..." \
  -d '{"tenant_type":"user","tenant_id":"Uxxx","budget_month":"2026-06-01","budgets":[{"budget_level":"total","amount":100000}]}'
```

## Unit tests

```bash
cd web
npm test -- --run src/lib/budget
```

Covers `health.ts`, `cascade.ts` (bucket resolution mirror of SQL).

## Periodic expenses

Auto-logged periodic rows (011) appear in budget spent without extra setup — verify by creating a schedule due today and triggering cron per `specs/011-periodic-expense-scheduler/quickstart.md`.

## Troubleshooting

| Symptom | Check |
| ------- | ----- |
| 403 on API | Tenant switcher matches `tenant_type`/`tenant_id`; user in `tenant_chat_members` for groups |
| Spent not updating | Expense `currency = JPY`, `deleted_at IS NULL`, `expense_date` in current month |
| Orphan budget row after category delete | Expected v1 — clear row in UI or SQL |
| Health always neutral on day 1 | Fixed: day 1 uses a 1-day time floor; heavy front-loaded spend shows over-pace colors |
| New fiscal month has no budgets | `get_budget_summary` / bot pace path lazy-copies from previous month via `lazy_copy_monthly_budgets` |
