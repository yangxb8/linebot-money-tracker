# Data Model: Expense Web Dashboard

**Feature**: 009-expense-web-dashboard  
**Extends**: [004 expense schema](../004-supabase-expense-storage/data-model.md), [006 group expenses](../006-group-expenses/spec.md), [007 tenant_chat_members](../007-llm-usage-limits/data-model.md)

## ERD

```text
auth.users (Supabase Auth)
        │
        │ 1:1
        ▼
line_auth_identities
        │
        │ maps to
        ▼
line_user_id ─────┬──────────────────────────────────┐
                  │                                  │
                  ▼                                  ▼
         user_language_preferences          tenant_chat_members
                  │                                  │
                  │                                  │ eligible tenants
                  ▼                                  ▼
              (UI locale)                    expenses / v_expenses_enriched
                                             (tenant_type, tenant_id)
```

## Entity: line_auth_identities (NEW)

Maps Supabase Auth users to LINE user IDs for RLS and UI.

| Column | Type | Notes |
| ------ | ---- | ----- |
| auth_user_id | uuid PK | FK → `auth.users(id)` ON DELETE CASCADE |
| line_user_id | text NOT NULL UNIQUE | LINE Login `sub` / `userId`; matches `expenses.line_user_id` |
| display_name | text NULL | From LINE profile (optional) |
| picture_url | text NULL | From LINE profile (optional) |
| linked_at | timestamptz NOT NULL DEFAULT now() | First link timestamp |
| updated_at | timestamptz NOT NULL DEFAULT now() | Last token exchange |

**RLS**: `SELECT` allowed for `auth.uid() = auth_user_id`; no client `INSERT`/`UPDATE`/`DELETE`.

## Entity: expenses (existing — RLS added)

No column changes. Read policy grants `SELECT` to `authenticated` when:

| Rule | Condition |
| ---- | --------- |
| Personal ledger | `tenant_type = 'user'` AND `tenant_id = current_line_user_id()` |
| Shared ledger | `tenant_type IN ('group','room')` AND user is in `tenant_chat_members` for same `(tenant_type, tenant_id)` |
| Active rows only (app filter) | `deleted_at IS NULL` (app also filters; RLS may allow deleted rows — app hides) |

**Write policy**: None for `authenticated` in MVP (read-only web).

## Entity: v_expenses_enriched (existing view)

Read-only enriched expense rows for dashboard list.

| Field (dashboard use) | Source |
| --------------------- | ------ |
| id | `expenses.id` |
| expense_date | `expenses.expense_date` |
| description | `expenses.description` |
| amount | `expenses.amount` |
| currency | `expenses.currency` |
| category_name_ja | view join |
| category_l1_name, l2, l3 | view join |
| tenant_type, tenant_id | `expenses` |
| logged_by_line_user_id | `expenses` |
| deleted_at | `expenses.deleted_at` |

**MVP filter**: `currency = 'JPY'` applied in client query.

## Entity: tenant_chat_members (existing — RLS added)

Used to populate tenant switcher and authorize shared-ledger reads.

| Column | Use in dashboard |
| ------ | ---------------- |
| tenant_type | `group` or `room` |
| tenant_id | LINE group/room ID |
| line_user_id | Must equal current user's LINE ID |

**RLS**: `SELECT` where `line_user_id = current_line_user_id()`.

## Entity: user_language_preferences (existing — RLS added)

| Column | Use in dashboard |
| ------ | ---------------- |
| line_user_id | Lookup key |
| reply_language | `ja` / `en` / `zh` for UI locale |

**RLS**: `SELECT` where `line_user_id = current_line_user_id()`.

## Entity: category_nodes (existing — RLS added)

**RLS**: `SELECT` to `authenticated` (read-only taxonomy; no user-specific rows).

## Helper function: current_line_user_id()

```sql
CREATE OR REPLACE FUNCTION current_line_user_id()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT line_user_id
  FROM line_auth_identities
  WHERE auth_user_id = auth.uid()
$$;
```

Used in RLS policies; returns NULL if unlinked (no rows returned).

## Tenant switcher model (application)

| Option label (i18n) | tenant_type | tenant_id |
| ------------------- | ----------- | --------- |
| Personal / 個人 | `user` | `current_line_user_id()` |
| Group {id} / グループ | `group` | from `tenant_chat_members` |
| Room {id} / ルーム | `room` | from `tenant_chat_members` |

Display names for groups/rooms: MVP shows shortened `tenant_id` or generic label; LINE chat title API is out of scope.

## State: Dashboard session

| State | Description |
| ----- | ----------- |
| anonymous | No Supabase session; redirect to `/login` |
| authenticated | Valid session + `line_auth_identities` row |
| tenant_selected | `tenant_type` + `tenant_id` in client state (default: personal) |
| list_loaded | Paginated rows cached per tenant |

## Indexes (existing, relied upon)

- `idx_expenses_tenant_date` on `(tenant_type, tenant_id, expense_date)` WHERE `deleted_at IS NULL`
- `tenant_chat_members` PK `(tenant_type, tenant_id, line_user_id)`

No new expense indexes required for MVP list queries.
