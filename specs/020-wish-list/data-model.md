# Data Model: Wish List

**Feature**: 020-wish-list

## ERD (conceptual)

```text
tenant (type, id)
    │
    ├──< wish_list_items >── category_nodes
    │         │
    │         │ executed_expense_id (optional)
    │         ▼
    └──< expenses >── wish_list_item_id (optional FK)
```

## Entity: wish_list_items

Planned purchase for a ledger.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | `gen_random_uuid()` |
| tenant_type | text NOT NULL | `user` / `group` / `room` |
| tenant_id | text NOT NULL | LINE userId or chat ID |
| name | text NOT NULL | Display name; trim length > 0 |
| amount | numeric(14,2) NOT NULL | Planned price; `>= 0` (0 allowed only if product later forbids — prefer `> 0` to match expenses/periodic) |
| currency | char(3) NOT NULL DEFAULT 'JPY' | MVP fixed JPY |
| category_node_id | uuid NOT NULL FK → category_nodes | Assigned category |
| category_l1_id | uuid NOT NULL FK → category_nodes | Denorm for budget impact |
| category_l2_id | uuid NULL FK → category_nodes | Denorm when assigned at L2/L3 |
| category_l3_id | uuid NULL FK → category_nodes | Optional denorm if expenses use L3 |
| assigned_level | smallint NOT NULL | 1 / 2 / 3 consistent with expenses |
| product_url | text NULL | Optional link; validated URL when present |
| sort_order | int NOT NULL | Manual priority among **active** items (lower = higher priority) |
| status | text NOT NULL DEFAULT 'active' | `active` \| `executed` |
| executed_expense_id | uuid NULL FK → expenses | Set on execute; used by executed filter |
| created_by_line_user_id | text NOT NULL | Actor who created (bot sender or web user) |
| created_at | timestamptz NOT NULL DEFAULT now() | |
| updated_at | timestamptz NOT NULL DEFAULT now() | |
| deleted_at | timestamptz NULL | Soft-delete for active items removed by user |

**Constraints**:

- `status IN ('active', 'executed')`
- `amount > 0` (align with expense/periodic checks)
- `currency = 'JPY'` for v1 (or allow column with app enforcing JPY)
- When `status = 'executed'`, `executed_expense_id IS NOT NULL`
- When `status = 'active'`, `executed_expense_id IS NULL`
- Soft-deleted rows (`deleted_at IS NOT NULL`) are not listed in active or executed UI

**Indexes**:

- `(tenant_type, tenant_id, status, sort_order)` — active list
- `(tenant_type, tenant_id, status, created_at DESC)` — created sort
- `(tenant_type, tenant_id, status, amount DESC)` — price sort
- `(executed_expense_id)` — join from executed view

**Uniqueness**: No unique constraint on name; duplicates allowed.

## Entity: expenses (delta)

| Column | Type | Notes |
| ------ | ---- | ----- |
| wish_list_item_id | uuid NULL FK → wish_list_items ON DELETE SET NULL | Set when expense created via execute |

**Index**: `(wish_list_item_id)` WHERE `wish_list_item_id IS NOT NULL`

Expense-card tag: `wish_list_item_id IS NOT NULL` (and `deleted_at IS NULL` for visibility).

## Derived: active list presentation

| Mode | Ordering |
| ---- | -------- |
| Priority (default) | `sort_order ASC`, tie-break `created_at ASC` |
| Created time | `created_at DESC` |
| Price | `amount DESC` (UI may reverse to ASC) |

Filter: `status = 'active' AND deleted_at IS NULL`.

## Derived: executed list presentation

Join `wish_list_items` → `expenses` on `executed_expense_id` (or via `wish_list_item_id`).

Display fields from **expense**: description/name, amount, category, expense_date, plus navigation to that expense. Do not show a separate pre-execute planned snapshot.

Filter: `wish_list_items.status = 'executed' AND wish_list_items.deleted_at IS NULL`.

## State transitions

```text
(create) → active
active → executed   # web execute success
active → deleted    # user delete (soft)
executed → (terminal for v1; no restore)
```

Concurrent execute/delete: second operation fails with clear conflict; client refreshes.

## Confirmation pending payload (bot, not a table)

Stored in existing `confirmation_messages` via `pending_action = 'wish_list_add'` and pending state JSON:

| Field | Notes |
| ----- | ----- |
| name | Extracted item name |
| amount | Extracted price |
| currency | `JPY` |
| category_node_id / denorm ids / assigned_level | From classify |
| product_url | Optional if extracted/URL in text |
| language | Reply language |

## Validation rules (app)

| Field | Rule |
| ----- | ---- |
| name | Required, non-empty after trim |
| amount | Required, numeric, `> 0` |
| category | Required, must belong to tenant |
| product_url | Optional; if set, valid http(s) URL |
| expense_date (execute) | Required date; default today in product TZ (Asia/Tokyo / existing rules) |

## Scale notes

Household ledgers; expect tens of active items. No archival job in v1.
