# Quickstart: Periodic Expense Scheduler

**Feature**: 011-periodic-expense-scheduler

## Prerequisites

- Features **009** and **010** complete (auth, drawer nav, tenant switcher, categories)
- Supabase env in `web/.env.local`: `NEXT_PUBLIC_SUPABASE_URL`, anon key, `SUPABASE_SERVICE_ROLE_KEY`
- New env (optional): `CRON_SECRET` for manual cron curl auth

## Apply migrations

```bash
# From repo root
supabase db push
# Or run SQL files manually:
# - supabase/migrations/20260623120000_periodic_expense_schedules.sql
# - supabase/migrations/20260623130000_periodic_expenses_cron.sql
```

Migration `20260623120000_periodic_expense_schedules` includes table, RLS, RPCs (`process_periodic_occurrence`, `process_due_periodic_schedules`), and category-delete trigger.

Migration `20260623130000_periodic_expenses_cron` enables `pg_cron` + `pg_net` and schedules hourly Edge Function invocation.

## Deploy Edge Function + cron

Vercel Hobby only allows daily cron, so production scheduling uses **Supabase pg_cron** (hourly, UTC).

### 1. Deploy the Edge Function

```bash
supabase functions deploy process-periodic-expenses --no-verify-jwt
```

Or deploy via Supabase Dashboard → Edge Functions.

### 2. Store service role key in Vault (one-time)

In Supabase SQL Editor, replace with your service role key:

```sql
SELECT vault.create_secret(
  '<SUPABASE_SERVICE_ROLE_KEY>',
  'supabase_service_role_key',
  'Auth for periodic expense pg_cron → Edge Function'
);
```

If the secret already exists, delete and recreate or use a new name and update the migration SQL.

### 3. Apply cron migration

```bash
supabase db push
```

Or run `supabase/migrations/20260623130000_periodic_expenses_cron.sql` manually.

Verify in Dashboard → **Integrations → Cron** (job `process-periodic-expenses-hourly`, schedule `0 * * * *`).

### 4. Optional: Edge Function secret for manual curl

```bash
supabase secrets set CRON_SECRET=<random-string>
```

## Vercel deploy (web UI only)

Deploy the Next.js app as usual. No Vercel cron is configured (`web/vercel.json` has no `crons` block).

`SUPABASE_SERVICE_ROLE_KEY` is only needed locally if you use the Next.js cron test route.

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

Create a schedule with `start_date = today` (JST), then either:

**Next.js route (local dev):**

```bash
curl -s -H "Authorization: Bearer $CRON_SECRET" \
  "http://localhost:3000/api/cron/process-periodic-expenses"
```

**Edge Function (deployed):**

```bash
curl -s -X POST \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  "https://nyuenufldaqsjybjhawl.supabase.co/functions/v1/process-periodic-expenses"
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
| Cron 401 | Vault secret `supabase_service_role_key` set; or `CRON_SECRET` matches curl header |
| Cron not running | Dashboard → Integrations → Cron; check `cron.job_run_details` |
| No expense after cron | `status = active`, `next_run_date <= today` in schedule timezone |
| Category picker empty | Visit Categories once to lazy-init tenant taxonomy (010) |
| Schedule paused unexpectedly | Category was deleted; reassign category and restart |
