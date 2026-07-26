# Wish List Web API Contract

**Feature**: 020-wish-list

Base path: `/api/wish-list`  
Auth: Supabase session required (same as dashboard).  
Tenant access: `assertTenantAccess` / `can_access_tenant` (same as periodic/budget).

## Common

**Tenant query/body params**:

| Param | Type | Description |
| ----- | ---- | ----------- |
| `tenant_type` | `user` \| `group` \| `room` | Ledger scope |
| `tenant_id` | string | LINE userId or chat ID |

---

## GET /api/wish-list

List wish items for a ledger.

**Query**: `tenant_type`, `tenant_id`, optional `status` (`active` default | `executed`), optional `sort` (`priority` default | `created` | `price`), optional `order` (`asc` \| `desc` — default depends on sort: priority asc, created desc, price desc)

**Response 200**:

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Headphones",
      "amount": 15000,
      "currency": "JPY",
      "category_node_id": "uuid",
      "category_name": "ガジェット",
      "product_url": "https://example.com/p/1",
      "sort_order": 0,
      "status": "active",
      "created_at": "2026-07-26T01:00:00Z",
      "executed_expense_id": null,
      "expense": null
    }
  ]
}
```

For `status=executed`, each item includes `expense` summary:

```json
{
  "executed_expense_id": "uuid",
  "expense": {
    "id": "uuid",
    "description": "Headphones",
    "amount": 14800,
    "currency": "JPY",
    "expense_date": "2026-07-26",
    "category_node_id": "uuid",
    "category_name": "ガジェット"
  }
}
```

---

## POST /api/wish-list

Create an active item.

**Body**:

```json
{
  "tenant_type": "user",
  "tenant_id": "Uxxx",
  "name": "Headphones",
  "amount": 15000,
  "category_node_id": "uuid",
  "product_url": "https://example.com/p/1"
}
```

**Behavior**: Assigns `sort_order` to end of active list. Denormalizes category L1/L2/L3 from `category_nodes`.

**Response 201**: created item object.

**Errors**: 400 validation; 403 tenant access; 404 category.

---

## PATCH /api/wish-list/[id]

Update an **active** item’s name, amount, category, and/or product_url.

**Body**: partial fields + tenant params.

**Errors**: 404; 409 if not active / deleted.

---

## DELETE /api/wish-list/[id]

Soft-delete an **active** item (`deleted_at = now()`). Not allowed for executed items (or no-op hide only if product chooses — v1: 409 on executed).

---

## POST /api/wish-list/reorder

Replace priority order for active items.

**Body**:

```json
{
  "tenant_type": "user",
  "tenant_id": "Uxxx",
  "ordered_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Behavior**: Sets `sort_order` to `0..n-1` for listed active ids belonging to tenant. Rejects if id set does not match current active set (or apply listed subset and append missing — prefer strict match for simplicity).

**Response 200**: `{ "ok": true }` or updated list.

---

## POST /api/wish-list/[id]/execute

Convert active item to expense.

**Body**:

```json
{
  "tenant_type": "user",
  "tenant_id": "Uxxx",
  "name": "Headphones",
  "amount": 14800,
  "category_node_id": "uuid",
  "expense_date": "2026-07-26"
}
```

**Defaults**: If fields omitted, use current wish item values; `expense_date` defaults to today (server TZ rules consistent with dashboard).

**Behavior**:
1. Verify item active and accessible.
2. Insert expense with confirmed fields + `wish_list_item_id = id`.
3. Set item `status=executed`, `executed_expense_id=expense.id`.

**Response 200**:

```json
{
  "item": { "id": "uuid", "status": "executed", "executed_expense_id": "uuid" },
  "expense": { "id": "uuid", "amount": 14800, "expense_date": "2026-07-26" }
}
```

**Errors**: 409 if already executed/deleted; 400 validation.

---

## Expense read shape (delta)

`ExpenseRecord` / list API includes:

| Field | Type | Notes |
| ----- | ---- | ----- |
| `wish_list_item_id` | `string \| null` | When non-null, UI shows wish-list tag |
