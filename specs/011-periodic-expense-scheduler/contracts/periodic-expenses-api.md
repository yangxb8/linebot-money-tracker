# Periodic Expenses API Contract

**Feature**: 011-periodic-expense-scheduler

Base path: `/api/periodic-expenses`  
Auth: Supabase session required (same as dashboard).

## Common

**Tenant query params** (list/create):

| Param | Type | Description |
| ----- | ---- | ----------- |
| `tenant_type` | `user` \| `group` \| `room` | Ledger scope |
| `tenant_id` | string | LINE userId or chat ID |

Server validates caller has access (matches RLS).

## Recurrence body shapes

See [data-model.md](../data-model.md). Server rejects unknown `kind` or invalid params.

## End condition body

| end_kind | Required fields |
| -------- | --------------- |
| `never` | — |
| `on_date` | `end_date` (date) |
| `amount_cap` | `end_amount_cap` (number > 0) |
| `repeat_count` | `end_repeat_limit` (int ≥ 1) |

## GET /api/periodic-expenses

List schedules for tenant.

**Query**: `tenant_type`, `tenant_id`

**Response 200**:

```json
{
  "schedules": [
    {
      "id": "uuid",
      "name": "家賃",
      "amount": 85000,
      "currency": "JPY",
      "assigned_level": 2,
      "category_l1_name": "住居",
      "category_l2_name": "家賃",
      "recurrence": { "kind": "monthly_days", "days": [1] },
      "recurrence_summary": "Monthly on 1st",
      "start_date": "2026-07-01",
      "timezone": "Asia/Tokyo",
      "end_kind": "never",
      "status": "active",
      "pause_reason": null,
      "next_run_date": "2026-07-01",
      "occurrence_count": 0,
      "cumulative_amount": 0,
      "created_by_line_user_id": "Uxxx",
      "created_at": "2026-06-23T10:00:00Z"
    }
  ]
}
```

Sorted by `next_run_date ASC NULLS LAST`, then `created_at DESC`.

## POST /api/periodic-expenses

Create schedule.

**Body**:

```json
{
  "tenant_type": "user",
  "tenant_id": "Uxxx",
  "name": "Netflix",
  "amount": 1490,
  "assigned_level": 2,
  "category_node_id": "uuid",
  "recurrence": { "kind": "monthly_days", "days": [15] },
  "start_date": "2026-06-15",
  "timezone": "Asia/Tokyo",
  "end_kind": "never"
}
```

**Response 201**: full schedule object with computed `next_run_date`, `status: "active"`.

**Errors**: 400 validation, 403 forbidden, 404 category not in tenant.

## GET /api/periodic-expenses/:id

Single schedule (tenant access enforced).

**Response 200**: schedule object.

## PATCH /api/periodic-expenses/:id

Update schedule fields. Recalculates `next_run_date` from `max(today_local, start_date)` when recurrence, start_date, or timezone changes.

**Body** (partial): any create fields except `tenant_type` / `tenant_id`.

**Response 200**: updated schedule.

**Notes**:
- Editing an `ended` schedule with revised end conditions may set `status` to `active` if client sends `"reactivate": true`.
- Cannot set `amount <= 0`.

## POST /api/periodic-expenses/:id/pause

**Response 200**: `{ "status": "paused", "pause_reason": "user" }`

**Errors**: 409 if already paused or ended.

## POST /api/periodic-expenses/:id/restart

Restart paused schedule.

**Body** (optional, required when `status === 'ended'`):

```json
{
  "end_kind": "never",
  "end_date": null,
  "end_amount_cap": null,
  "end_repeat_limit": null
}
```

**Response 200**: schedule with `status: "active"` and new `next_run_date`.

**Errors**:
- 409 if ended and end conditions unchanged
- 409 if `pause_reason === 'category_missing'` until category reassigned via PATCH

## DELETE /api/periodic-expenses/:id

Hard delete schedule row. Does not delete linked expenses.

**Response 204**

## POST /api/periodic-expenses/preview-next (optional helper)

Compute next run dates for form UX without saving.

**Body**: `{ "recurrence", "start_date", "timezone", "after": "2026-06-23" }`

**Response 200**: `{ "next_run_date": "2026-07-01", "following_run_date": "2026-08-01" }`

## Client read alternative

Authenticated Supabase client may `select` from `periodic_expense_schedules` with RLS directly for list if API shaping is not needed — MVP uses API for enriched category names and consistent validation.
