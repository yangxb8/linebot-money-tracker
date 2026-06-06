# Contract: Categorization Reply

**Feature**: 004-supabase-expense-storage  
**Modules**: `services/categorize.py`, `services/message_handler.format_expense_items`

## LLM output schema

```json
{
  "guessed_category_code": "food.dining.cafe",
  "alternatives": ["food.dining.restaurant", "food.grocery", "unknown"]
}
```

**Rules**:
- `guessed_category_code` MUST exist in taxonomy (or map to `unknown`)
- `alternatives` MUST contain 0–3 distinct codes from taxonomy, excluding the guess
- Codes validated server-side; invalid codes replaced with `unknown`

## User-facing reply structure

For each expense item:

```text
Detected expense(s):
- {description}: {amount} {currency}
  Category (guess): {L1} > {L2} > {L3}   # omit empty levels
  Please confirm or pick another:
  1) {alt path 1}
  2) {alt path 2}
  3) {alt path 3}
  Reply to this message to change category (1–3), edit fields, delete, or restore.
```

**Rules**:
- Always show guess path (may be `不明` for unknown)
- Show up to 3 numbered alternatives when LLM provides them
- Omit alternatives section lines when fewer than 1 alternative returned
- **MUST NOT** include budget impact text (FR-010)

## User correction flow

When user **replies to the confirmation message** with `1`, `2`, or `3`, or natural-language edits:
- Handled by feature **005-expense-reply-edits** — see [005 quickstart](../../005-expense-reply-edits/quickstart.md)
- Category picks and field updates persist to `expenses` via repository mutators
- Soft-delete / restore supported with action summaries

## Multi-item receipts

Each item gets its own category block under the same reply message. All items share `source_message_id` but distinct `line_item_index` in DB.
