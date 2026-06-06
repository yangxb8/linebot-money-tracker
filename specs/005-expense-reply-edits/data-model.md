# Data Model: Expense Reply Edits

**Feature**: 005-expense-reply-edits  
**Extends**: [004 data-model](../004-supabase-expense-storage/data-model.md)

## ERD (delta)

```text
confirmation_messages ──< confirmation_expenses >── expenses
        │
        ├──< reply_edit_audit
        │
processed_reply_messages (idempotency)
```

## Entity: confirmation_messages (new)

One row per bot expense confirmation sent to a user.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | |
| bot_message_id | text UNIQUE NOT NULL | LINE SentMessage.id or console synthetic ID |
| line_user_id | text NOT NULL | Owner |
| confirmation_text | text NOT NULL | Snapshot of full reply sent |
| items_snapshot | jsonb NOT NULL | Per-item metadata (see below) |
| pending_action | text NULL | `'delete_all'` or NULL |
| created_at | timestamptz NOT NULL DEFAULT now() | |

**items_snapshot** element shape:

```json
{
  "line_item_index": 0,
  "expense_id": "uuid",
  "description": "Coffee",
  "amount": 450.0,
  "currency": "JPY",
  "category_guess_code": "food.dining.cafe",
  "category_alternatives": ["food.dining.restaurant", "food.grocery", "unknown"]
}
```

## Entity: confirmation_expenses (new)

| Column | Type | Notes |
| ------ | ---- | ----- |
| confirmation_id | uuid FK → confirmation_messages | |
| expense_id | uuid FK → expenses | |
| line_item_index | int NOT NULL | Matches expense row |

**Unique**: `(confirmation_id, expense_id)`

## Entity: expenses (altered)

| Column | Type | Notes |
| ------ | ---- | ----- |
| deleted_at | timestamptz NULL | NULL = active; set on soft-delete |
| updated_at | timestamptz NOT NULL DEFAULT now() | Bump on mutation |

Rollup RPCs and app queries for active expenses: `WHERE deleted_at IS NULL`.

## Entity: reply_edit_audit (new)

Append-only audit for FR-014.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | |
| confirmation_id | uuid FK | |
| line_user_id | text NOT NULL | |
| user_reply_message_id | text NOT NULL | Inbound message ID |
| user_reply_text | text NOT NULL | |
| intent_json | jsonb NOT NULL | Parsed EditIntent |
| result_status | text NOT NULL | `applied`, `clarification`, `no_op`, `error` |
| result_summary | text | Bot message sent |
| created_at | timestamptz NOT NULL DEFAULT now() | |

## Entity: processed_reply_messages (new)

| Column | Type | Notes |
| ------ | ---- | ----- |
| line_user_id | text NOT NULL | |
| user_reply_message_id | text NOT NULL | |
| processed_at | timestamptz NOT NULL DEFAULT now() | |

**Unique**: `(line_user_id, user_reply_message_id)`

## Application types (not persisted)

### ReplyContext

| Field | Source |
| ----- | ------ |
| line_user_id | LINE source.user_id |
| user_reply_message_id | Inbound message.id |
| quoted_bot_message_id | message.quotedMessageId |

### EditIntent (LLM JSON → validated)

See [reply-edit-intent.md](./contracts/reply-edit-intent.md).

## State transitions

### Expense active/deleted

```text
[active] ──soft_delete──► [deleted_at set]
[deleted] ──restore / restore_all──► [active]
[active] ──update fields──► [active, updated_at bumped]
```

### Confirmation pending_action

```text
NULL ──user: delete all──► delete_all ──user: YES──► NULL (expenses soft-deleted)
delete_all ──user: cancel/other──► NULL (optional) or remain until YES
```

### Reply processing

```text
[Inbound reply]
  → load confirmation by quoted_bot_message_id
  → idempotency check processed_reply_messages
  → parse EditIntent (LLM JSON)
  → if clarification → summary, no DB mutation
  → else apply repository mutators + audit log
  → format summary (language matched)
```

## Relationships to existing code

- After `insert_expenses` + `format_expense_items`, `confirmation_repository.save_confirmation(...)` with sent message ID.
- `message_handler.process_reply_edit` replaces log path when `ReplyContext.quoted_bot_message_id` set.
- `expense_repository.build_insert_row` unchanged; updates go through new mutators.
