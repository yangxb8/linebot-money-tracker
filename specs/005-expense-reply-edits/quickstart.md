# Quickstart: Expense Reply Edits

**Feature**: 005-expense-reply-edits  
**Branch**: `005-expense-reply-edits`  
**Depends on**: [004 quickstart](../004-supabase-expense-storage/quickstart.md) (expense logging + Supabase)

## Prerequisites

- Feature 004 implemented: expenses persist, confirmation replies include category guess + alternatives
- Migration `20260606130000_expense_reply_edits.sql` applied
- `.env` with `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

## 1. Log an expense (get confirmation ID)

```bash
python local_run.py --text "スーパー 3500円"
```

When confirmation saving is wired, stdout includes a line like:

```text
[confirmation] bot_message_id=console-a1b2c3d4-... (use with --reply-to)
```

Note the `bot_message_id` for reply testing.

## 2. Edit via simulated reply

```bash
python local_run.py --reply-to console-a1b2c3d4-... --text "3800円に修正"
```

Expected: action summary describing amount change (Japanese if reply is Japanese).

## 3. Category pick (single item)

```bash
python local_run.py --reply-to <id> --text "2"
```

Expected: category updated to alternative 2 from original confirmation.

## 4. Soft delete and restore

```bash
python local_run.py --reply-to <id> --text "delete"
python local_run.py --reply-to <id> --text "restore"
```

## 5. Delete all (multi-item receipt)

After logging a multi-item receipt:

```bash
python local_run.py --reply-to <id> --text "delete all"
# Bot asks for confirmation
python local_run.py --reply-to <id> --text "YES"
```

Restore all:

```bash
python local_run.py --reply-to <id> --text "restore all"
```

## 6. Verify in Supabase

```sql
SELECT id, description, amount, deleted_at, updated_at
FROM expenses
WHERE line_user_id = 'local-dev-user'
ORDER BY updated_at DESC
LIMIT 5;

SELECT bot_message_id, pending_action, created_at
FROM confirmation_messages
ORDER BY created_at DESC
LIMIT 3;

SELECT result_status, result_summary, created_at
FROM reply_edit_audit
ORDER BY created_at DESC
LIMIT 5;
```

## 7. LINE webhook flow

1. User sends expense → bot replies with confirmation (SentMessage ID saved).
2. User **replies** to that message in LINE chat.
3. Webhook receives text with `quotedMessageId` → edit pipeline runs.

## 8. Run tests

```bash
python -m pytest tests/test_reply_edit.py tests/test_confirmation_repository.py tests/test_message_handler_reply.py -q
python -m pytest -q
```

## Troubleshooting

| Issue | Check |
| ----- | ----- |
| "Cannot edit this message" | `quotedMessageId` must match stored `bot_message_id` |
| Bare `2` ignored on multi-item | Identify item first (`coffee: 2`) |
| Delete-all did nothing | Reply YES after confirmation prompt |
| Totals still include deleted | RPC migration applied (`deleted_at IS NULL` filter) |
| Duplicate edit on retry | `processed_reply_messages` unique constraint |
