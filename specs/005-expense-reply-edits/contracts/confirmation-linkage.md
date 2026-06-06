# Contract: Confirmation Linkage

**Feature**: 005-expense-reply-edits  
**Module**: `services/confirmation_repository.py`

## Save (after expense log + bot send)

**Trigger**: Successful expense detection, persistence, and confirmation reply sent to user.

**Input**:

```python
save_confirmation(
    bot_message_id: str,          # LINE SentMessage.id
    line_user_id: str,
    confirmation_text: str,
    items: list[ConfirmationItemSnapshot],
) -> str  # confirmation uuid
```

**ConfirmationItemSnapshot**:

```python
line_item_index: int
expense_id: str               # uuid from insert result
description: str
amount: Decimal
currency: str
category_guess_code: str
category_alternatives: list[str]  # 0-3 codes
```

**Database**: INSERT `confirmation_messages` + rows in `confirmation_expenses`.

**Console mode**: `bot_message_id` = `console-{uuid4()}` printed to stdout after log for use with `--reply-to`.

## Load (on user reply)

**Trigger**: Inbound text with `quoted_bot_message_id`.

```python
get_confirmation_by_bot_message_id(
    bot_message_id: str,
    line_user_id: str,
) -> ConfirmationRecord | None
```

**Authorization**: MUST match `line_user_id` (FR-003).

## Pending action

```python
set_pending_action(confirmation_id: str, action: str | None) -> None
# action: "delete_all" or None
```

## Idempotency

```python
try_mark_reply_processed(line_user_id: str, user_reply_message_id: str) -> bool
# Returns False if already processed (skip mutations)
```

## Audit

```python
write_audit(
    confirmation_id: str,
    line_user_id: str,
    user_reply_message_id: str,
    user_reply_text: str,
    intent_json: dict,
    result_status: str,
    result_summary: str,
) -> None
```
