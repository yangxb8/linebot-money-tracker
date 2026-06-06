# Contract: LLM Reply-Edit Boundary

**Feature**: 005-expense-reply-edits  
**Extends**: [004 llm-db-boundary.md](../004-supabase-expense-storage/contracts/llm-db-boundary.md)

## Rule

**The LLM MUST NOT generate or execute SQL** for reply edits. It produces **structured EditIntent JSON** only. The Python application validates JSON and performs mutations through **named repository methods**.

## LLM responsibilities (JSON only)

| Stage | Module | Output |
| ----- | ------ | ------ |
| Parse user reply | `reply_edit.parse_edit_intent` | `EditIntent` JSON ([reply-edit-intent.md](./reply-edit-intent.md)) |

Prompt includes: confirmation `items_snapshot`, user reply text, `pending_action` state, supported languages note.

## Application responsibilities (no LLM)

| Step | Module | Action |
| ---- | ------ | ------ |
| Load confirmation | `confirmation_repository.get_by_bot_message_id` | Fixed SELECT |
| Idempotency | `confirmation_repository.mark_reply_processed` | Fixed INSERT |
| Resolve numbered category pick | `reply_edit.resolve_category_pick` | Map 1–3 using snapshot alternatives |
| Update fields | `expense_repository.update_expense_fields` | Fixed UPDATE by expense id |
| Soft-delete / restore | `expense_repository.soft_delete_expenses` / `restore_expenses` | Fixed UPDATE `deleted_at` |
| Pending delete-all | `confirmation_repository.set_pending_action` | Fixed UPDATE |
| User summary | `reply_summary.format_edit_result` | Python templates (not LLM) |
| Audit | `confirmation_repository.write_audit` | Fixed INSERT |

## Forbidden patterns

- LLM-generated UPDATE/DELETE SQL
- Dynamic column names from LLM output
- LLM-generated user summary as sole source of truth (must match applied DB state)

## Error handling

| Failure | Behavior |
| ------- | -------- |
| Invalid EditIntent JSON | Clarification reply; no mutation |
| Unknown confirmation | Guidance: reply to expense confirmation message |
| Target item ambiguous (multi-item) | Clarification reply; no mutation |
| DB mutation failure | Friendly error; audit `error` status |
