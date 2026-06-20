# Categories API Contract

**Feature**: 010-tenant-category-editor

Base path: `/api/categories`  
Auth: Supabase session required (same as dashboard).

## Common

**Tenant query params** (all routes):

| Param | Type | Description |
| ----- | ---- | ----------- |
| `tenant_type` | `user` \| `group` \| `room` | Ledger scope |
| `tenant_id` | string | LINE userId or chat ID |

Server validates caller has access (matches RLS).

## GET /api/categories

Lazy-initializes taxonomy if needed; returns full tree.

**Response 200**:

```json
{
  "initialized": true,
  "nodes": [
    {
      "id": "uuid",
      "code": "food",
      "name_ja": "食費",
      "level": 1,
      "parent_id": null,
      "sort_order": 1,
      "expense_count": 12,
      "deletable": false
    }
  ]
}
```

- `deletable: false` for `unknown` and last remaining L1.
- `expense_count` optional aggregate for delete UX.

## POST /api/categories

Create L1 or L2.

**Body**:

```json
{
  "tenant_type": "user",
  "tenant_id": "Uxxx",
  "level": 2,
  "parent_id": "uuid-of-l1",
  "name_ja": "ペットフード"
}
```

**Response 201**: created node object with generated `code`.

**Errors**: 400 validation, 403 forbidden, 409 duplicate name under parent (optional).

## PATCH /api/categories/:id

Rename or reorder.

**Body** (partial):

```json
{
  "name_ja": "食費・飲料",
  "sort_order": 2
}
```

**Response 200**: updated node.

## POST /api/categories/:id/delete

Delete node; transfer required when expenses exist.

**Body**:

```json
{
  "tenant_type": "user",
  "tenant_id": "Uxxx",
  "transfer_to_id": "uuid-of-target-l1-or-l2"
}
```

Omit `transfer_to_id` only when `expense_count === 0`.

**Response 200**:

```json
{
  "deleted_id": "uuid",
  "transferred_expenses": 5
}
```

**Errors**:
- 400: transfer required but missing; invalid target; cannot delete `unknown` or last L1
- 403: not a member
- 404: node not found

## Error envelope

```json
{
  "error": "transfer_required",
  "message": "このカテゴリには5件の支出があります。移行先を選択してください。"
}
```

## i18n

API `message` keys map to `web/src/lib/i18n/messages.ts`; client may localize by code.
