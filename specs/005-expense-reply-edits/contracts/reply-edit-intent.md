# Contract: Reply Edit Intent (LLM JSON)

**Feature**: 005-expense-reply-edits  
**Module**: `services/reply_edit.py`

## Schema

```json
{
  "action": "update",
  "target": {
    "mode": "single",
    "line_item_index": 0,
    "description_hint": "Coffee"
  },
  "updates": {
    "amount": 3800,
    "currency": "JPY",
    "description": "Supermarket",
    "expense_date": "2026-06-05",
    "category_code": "food.grocery",
    "category_alternative_number": 2
  },
  "clarification_needed": false,
  "clarification_message": null
}
```

## action enum

| Value | Meaning |
| ----- | ------- |
| `update` | Apply field changes in `updates` |
| `soft_delete` | Soft-delete target expense(s) |
| `soft_delete_all` | Request bulk delete (sets pending; does not delete yet) |
| `restore` | Restore soft-deleted target |
| `restore_all` | Restore all soft-deleted on confirmation |
| `confirm_pending` | Affirmative response when `pending_action = delete_all` |
| `clarify` | No mutation; use `clarification_message` |

## target.mode enum

| Value | When |
| ----- | ---- |
| `single` | One expense; use `line_item_index` and/or `description_hint` |
| `all_active` | All non-deleted linked expenses |
| `all_deleted` | All soft-deleted linked expenses (restore_all) |
| `unspecified` | Parser could not identify item — app asks user |

## updates (all optional except when action=update)

| Field | Validation |
| ----- | ---------- |
| `amount` | positive number |
| `currency` | 3-letter ISO |
| `description` | non-empty string |
| `expense_date` | ISO date; interpreted JST |
| `category_code` | taxonomy code or maps to unknown |
| `category_alternative_number` | int 1–3; resolved via confirmation snapshot |

## Numbered category rules (app-enforced after JSON parse)

- **Single-item confirmation**: `category_alternative_number` alone is sufficient.
- **Multi-item confirmation**: `target` MUST identify item; bare number without item → force `clarify`.

## Affirmative detection (confirm_pending)

When `pending_action = delete_all`, map YES / はい / 是 / confirm to `confirm_pending`.

## Delete phrase detection (deterministic, before LLM)

| User phrase | Items | action |
| ----------- | ----- | ------ |
| `cancel`, `delete`, `取消`, `删除`, `キャンセル`, … | 1 | `soft_delete` |
| Same phrases | 2+ | `soft_delete_all` (YES confirmation) |
| `delete all`, `全部取消`, `全部删除`, `取消全部`, `削除全部`, … | any | `soft_delete_all` |
| `取消`, `cancel`, `いいえ`, `算了`, … | pending `delete_all` | `cancel_pending` |

User MUST reply to the **bot confirmation message** (LINE reply-to) for YES / cancel-pending on bulk delete.

## Validation

`jsonschema` Draft7; invalid → treat as `clarify` with generic message.

## Languages

Prompt instructs model to interpret JP/EN/ZH user text; `clarification_message` SHOULD match user language when possible (app may override via `reply_summary`).
