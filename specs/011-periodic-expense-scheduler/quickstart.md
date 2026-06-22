# Quickstart: Periodic Expense Scheduler

**Feature**: 011-periodic-expense-scheduler

## Prerequisites

- Features **009** and **010** complete (auth, drawer nav, tenant switcher, categories)
- Supabase env in `web/.env.local`: `NEXT_PUBLIC_SUPABASE_URL`, anon key, `SUPABASE_SERVICE_ROLE_KEY`
- New env: `CRON_SECRET` (random string for cron auth)

## Apply migration

```bash
# From repo root
supabase db push
# Or run supabase/migrations/20260623120000_periodic_expense_schedules.sql manually
```

Migration `20260623120000_periodic_expense_schedules` includes table, RLS, RPCs (`process_periodic_occurrence`, `process_due_periodic_schedules`), and category-delete trigger.

## Vercel deploy

1. Add `CRON_SECRET` to Vercel project env (Production + Preview) — required for hourly cron auth
2. Confirm `SUPABASE_SERVICE_ROLE_KEY` is set (server only; used by cron route)
3. Deploy — Vercel enables cron from `web/vercel.json` (`0 * * * *`)
4. After deploy, check **Functions → Cron** logs for `[cron:periodic-expenses]` count lines (no PII)

## Local web

```bash
cd web && npm install && npm run dev
```

1. Sign in at `http://localhost:3000/login`
2. Open drawer (☰) → **Periodic Expenses**
3. Create a schedule: name, category, amount, recurrence, start date
4. Confirm card shows amount, frequency summary, next run date

## Test recurrence engine

```bash
cd web && npm test -- recurrence
```

## Trigger cron locally

Create a schedule with `start_date = today` (JST), then:

```bash
curl -s -H "Authorization: Bearer $CRON_SECRET" \
  "http://localhost:3000/api/cron/process-periodic-expenses"
```

1. Open **Expenses** — new row with schedule name as description
2. Refresh Periodic Expenses — `occurrence_count` incremented, `next_run_date` advanced

## Pause / restart

1. Pause an active schedule from card actions
2. Trigger cron — no new expense
3. Restart — `next_run_date` is on or after today (no backfill for missed days)

## Group schedule

```bash
python local_run.py --group-id <group_id> --text "テスト 100円"
```

1. Select group in tenant switcher
2. Create periodic expense for group tenant
3. Another group member signs in, switches to same group — sees shared schedule

## End conditions (manual)

| Type | Setup | Verify |
| ---- | ----- | ------ |
| `repeat_count = 1` | start today | One expense after cron; status `ended` |
| `amount_cap` | amount 1000, cap 2000 | Two runs then ended |
| `on_date` | end today | Runs today if due; ended after |

## Tests

```bash
cd web && npm test
# Recurrence unit tests + API validation tests when added
```

SQL RLS check (personal cross-tenant deny):

```sql
-- As authenticated user A, should return 0 rows for user B tenant
SELECT * FROM periodic_expense_schedules
WHERE tenant_type = 'user' AND tenant_id = '<other_user_id>';
```

## Troubleshooting

| Issue | Check |
| ----- | ----- |
| Cron 401 | `CRON_SECRET` matches Vercel env and curl header |
| No expense after cron | `status = active`, `next_run_date <= today` in schedule timezone |
| Category picker empty | Visit Categories once to lazy-init tenant taxonomy (010) |
| Schedule paused unexpectedly | Category was deleted; reassign category and restart |
