# Contract: Cron Processing

**Feature**: 011-periodic-expense-scheduler

## Runtime

**Supabase Edge Function** `process-periodic-expenses`, scheduled hourly by **pg_cron** + **pg_net** (migration `20260623130000_periodic_expenses_cron.sql`).

Vercel Hobby limits cron to once per day, so production scheduling lives in Supabase—not Vercel.

The Next.js route `GET /api/cron/process-periodic-expenses` remains for **local manual testing** only.

## Authentication

Edge Function accepts either:

```http
Authorization: Bearer <CRON_SECRET>
```

or (used by pg_cron):

```http
apikey: <SUPABASE_SERVICE_ROLE_KEY>
```

Store the service role key in Supabase Vault as `supabase_service_role_key` (see quickstart). Optional: set `CRON_SECRET` in Edge Function secrets for manual curl.

`verify_jwt = false` on the function; auth is enforced in handler code.

## pg_cron schedule

```sql
-- 0 * * * * — minute 0 every hour UTC
SELECT cron.schedule('process-periodic-expenses-hourly', '0 * * * *', ...);
```

Due schedules are evaluated against each row's `timezone`.

## Handler behavior

1. Validate `CRON_SECRET` or service-role `apikey`.
2. Create Supabase client with `SUPABASE_SERVICE_ROLE_KEY` (auto-injected in Edge Functions).
3. Load active schedules, compute due actions in TypeScript (recurrence engine).
4. Call `rpc('process_due_periodic_schedules', { p_actions })`.
5. Log aggregate counts (no schedule names or user IDs).
6. Return **200** with JSON body.

**Response 200**:

```json
{
  "processed": 12,
  "inserted": 10,
  "skipped": 2,
  "ended": 1
}
```

**Response 500**: RPC or DB failure; pg_cron retries next hour.

## Idempotency

- Unique `(periodic_schedule_id, expense_date)` on expenses prevents duplicate rows.
- RPC uses row lock and idempotent insert.
- Re-running cron same hour: `skipped` increments, no duplicate expenses.

## Local manual trigger

**Next.js (local dev)**:

```bash
curl -s -H "Authorization: Bearer $CRON_SECRET" \
  "http://localhost:3000/api/cron/process-periodic-expenses"
```

**Edge Function (deployed or `supabase functions serve`)**:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $CRON_SECRET" \
  "https://<project-ref>.supabase.co/functions/v1/process-periodic-expenses"
```

Or with service role:

```bash
curl -s -X POST \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  "https://<project-ref>.supabase.co/functions/v1/process-periodic-expenses"
```

## Expense row shape (cron insert)

| Column | Value |
| ------ | ----- |
| tenant_type | from schedule |
| tenant_id | from schedule |
| logged_by_line_user_id | schedule.created_by_line_user_id |
| line_user_id | schedule.created_by_line_user_id |
| source_message_id | `periodic:{schedule_id}:{YYYY-MM-DD}` |
| line_item_index | 0 |
| description | schedule.name |
| amount | schedule.amount |
| currency | schedule.currency |
| expense_date | schedule.next_run_date (local occurrence date) |
| category_node_id | schedule.category_node_id |
| assigned_level | schedule.assigned_level |
| category_l1_id | schedule.category_l1_id |
| category_l2_id | schedule.category_l2_id |
| periodic_schedule_id | schedule.id |

## Monitoring

- Edge Function logs: Supabase Dashboard → Edge Functions → `process-periodic-expenses`
- pg_cron history: `SELECT * FROM cron.job_run_details WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'process-periodic-expenses-hourly') ORDER BY start_time DESC LIMIT 10;`
- Log aggregate counts per run.

## Out of scope

- Sub-minute scheduling
- Per-user push notifications after insert
- Dead-letter queue for failed inserts (retry next hour via idempotency)
