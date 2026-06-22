# Contract: Cron Processing

**Feature**: 011-periodic-expense-scheduler

## Route

`GET /api/cron/process-periodic-expenses`

Vercel Cron invokes this path on the schedule defined in `web/vercel.json`.

## Authentication

Request MUST include header:

```http
Authorization: Bearer <CRON_SECRET>
```

Compare to `process.env.CRON_SECRET`. Return **401** if missing or mismatch.

Vercel also sends `x-vercel-cron: 1` — log but do not rely on it alone for auth.

## vercel.json

```json
{
  "crons": [
    {
      "path": "/api/cron/process-periodic-expenses",
      "schedule": "0 * * * *"
    }
  ]
}
```

Runs at minute 0 every hour UTC. Due schedules evaluated against each row's `timezone`.

## Handler behavior

1. Validate `CRON_SECRET`.
2. Create Supabase client with `SUPABASE_SERVICE_ROLE_KEY`.
3. Call `rpc('process_due_periodic_schedules', { p_as_of: new Date().toISOString() })`.
4. Log result counts (no schedule names or user IDs in production logs).
5. Return **200** with JSON body from RPC.

**Response 200**:

```json
{
  "processed": 12,
  "inserted": 10,
  "skipped": 2,
  "ended": 1
}
```

**Response 500**: RPC or DB failure; Vercel retries next hour.

## Idempotency

- Unique `(periodic_schedule_id, expense_date)` on expenses prevents duplicate rows.
- RPC should use row lock or `INSERT ... ON CONFLICT DO NOTHING` on expenses.
- Re-running cron same hour: `skipped` increments, no duplicate expenses.

## Local manual trigger

```bash
curl -s -H "Authorization: Bearer $CRON_SECRET" \
  "http://localhost:3000/api/cron/process-periodic-expenses"
```

Requires `CRON_SECRET` and `SUPABASE_SERVICE_ROLE_KEY` in `web/.env.local`.

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

- Log aggregate counts per run.
- Alert if `inserted = 0` and `processed > 0` with all `skipped` for 24h (optional ops).

## Out of scope

- Sub-minute scheduling
- Per-user push notifications after insert
- Dead-letter queue for failed inserts (retry next hour via idempotency)
