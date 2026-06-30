# Budget Pace Reply Contract

**Feature**: 015-budget-pace-alert  
**Type**: Bot reply prepend contract

## Module

- `services/budget_pace.py` — `format_pace_warnings(warnings, language) -> str`
- `services/budget_pace_prompt.py` — LLM prompt builder (optional)
- `services/budget_pace_i18n.py` — template fallback strings

## Prepend helper

### `maybe_prepend_budget_pace_warning(body, *, expense_rows, tenant, language, gemini=None) -> str`

**Behavior**:

1. Call `evaluate_pace_warnings(expense_rows, tenant)`
2. If empty → return `body` unchanged
3. Format warning block via LLM (if `gemini` provided) or template
4. Return `f"{warning_block}\n\n{body}"`

**FR-013**: Any exception in steps 1–3 → return `body` unchanged; log exception.

## Warning content requirements (FR-007)

Each warning block MUST include:

| Element | Example (ja) |
| ------- | ------------ |
| Emoji | ⚠️ or 🚨 at start |
| Ahead-of-pace indication | ペースが速いです |
| Category / level name | 外食 / 食費 / 今月の総予算 |
| Daily allowance | 残り20日で1日あたり約¥250まで |

## LLM prompt contract

When Gemini is available:

```text
System: You write a single short budget pace warning for a LINE chat reply.
User: Language: {language}
Budget level: {level} ({display_name})
Remaining budget: ¥{remaining}
Days left in month: {days_remaining}
Recommended daily spend: ¥{daily_allowance}
The user is spending faster than expected this month.
Write 1-2 sentences. Start with an emoji. Include the daily ¥ figure. Do not repeat expense details.
```

**Metering**: `llm_operation_scope('budget_pace')` with `operation_type='budget_pace'`.

## Template fallback (`budget_pace_i18n.py`)

| Key | ja | en |
| --- | -- | -- |
| `pace_warning_l2` | ⚠️ **{name}** の支出ペースが速いです。残り{days}日は1日約¥{daily}までが目安です。 | ⚠️ You're spending **{name}** too fast. Aim for about ¥{daily}/day for the next {days} days. |
| `pace_warning_l1` | (same pattern for L1) | |
| `pace_warning_total` | ⚠️ 今月の**総予算**のペースが速いです。... | ⚠️ You're ahead of your **total budget** pace... |
| `pace_exhausted` | 予算を使い切りました | Budget exhausted |

## Integration points

| Call site | When | `expense_rows` source |
| --------- | ---- | ----------------------- |
| `message_handler._enrich_and_persist_items` | After successful `insert_expenses` | Enriched items with DB fields |
| `reply_edit.apply_edit_intent` | After `update` with amount/category change | Updated expense row(s) from confirmation |

## Reply shape

```text
⚠️ 外食の支出ペースが速いです。残り20日は1日約¥250までが目安です。

検出した支出:
...
```

Blank line separation required (SC-004 / User Story 3).

## Languages

`ja`, `en`, `zh` — same set as `confirmation_i18n.py` / `reply_summary.py`.

## Out of scope

- Modifying `confirmation_payload` structure
- Storing warning text in audit log (optional future enhancement)
- Web dashboard surfaces
