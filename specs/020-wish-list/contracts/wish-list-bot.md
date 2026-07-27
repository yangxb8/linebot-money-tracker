# Wish List Bot Contract

**Feature**: 020-wish-list  
**Type**: Internal Python service + webhook integration

## Intent classification

### Module

`services/intent.py`

### Change

`TextMessageIntent = Literal['expense', 'webapp', 'wish_list', 'other']`

`COMBINED_TEXT_INTENT_PROMPT` adds:

- `wish_list`: user wants to record something they have **not purchased yet** / plan to buy (e.g. “I want to buy…”, “買いたい”, “欲しい”, “wishlist”, “まだ買ってない”).
- Prefer `wish_list` over `expense` when not-yet-purchased intent is clear.
- Prefer `expense` when the message clearly logs a completed purchase.

Optional deterministic phrase gate (same module or `message_handler`) may short-circuit obvious wish phrases before LLM.

### Function

`classify_text_message_intent(text, gemini) -> TextMessageIntent`  
Must accept/return `wish_list`.

---

## Message handling branch

### Module

`services/message_handler.py`

### Text path

After intent classification:

| Intent | Behavior |
| ------ | -------- |
| `wish_list` with extractable name+price | Extract without `insert_expenses`; categorize; budget impact; save confirmation with `pending_action='wish_list_add'` |
| `wish_list` without enough detail | Ask what to buy (reply with text or photo); save confirmation with `pending_action='wish_list_await_details'` |
| `expense` | Existing behavior unchanged |
| others | Existing behavior unchanged |

### Reply to `wish_list_await_details`

User must **reply to** the bot ask message (LINE quote/reply):

| Reply | Behavior |
| ----- | -------- |
| Cancel (`no` / `不用` / …) | Clear pending; no wish item |
| Text with product+price | Parse → budget impact → upgrade pending to `wish_list_add` (re-anchor interaction message id) |
| Image | Extract product → same as text details path |
| Unparseable | Re-ask details; keep `wish_list_await_details` |

Image messages that are **not** a reply to this pending confirmation continue through the normal expense image flow.

### Image path

`process_image_message(..., accompanying_text: str | None = None)` (signature evolution):

- If `accompanying_text` has wish intent → wish flow using image extraction for candidate fields.
- If no accompanying text → existing image expense flow.

`local_run.py`: allow `--image` together with `--text` for this path.

---

## Budget impact helper

### Module

`services/wish_list_budget.py` (new)

### Function

`build_wish_list_budget_impact(tenant, amount, category_path, currency='JPY', as_of_date=None) -> WishBudgetImpact`

**Returns** (conceptual):

```python
@dataclass
class WishBudgetImpact:
    has_budget: bool
    level: str | None          # 'l2' | 'l1' | 'total' | None
    label: str | None          # category or total label
    limit: float | None
    spent_now: float | None
    remaining_now: float | None
    remaining_if_purchased: float | None
    is_ahead_if_purchased: bool
    days_remaining: int | None
    daily_allowance_if_purchased: float | None
```

**Rules**:
- Use `fetch_budget_summary` + cascade evaluation from `budget_pace.py`.
- Pick the lowest applicable budget level for messaging (same specificity preference as 015).
- Always populate remaining_now / remaining_if_purchased when `has_budget`.
- Set `is_ahead_if_purchased` using health/pace on hypothetical spent (`spent + amount`).
- On RPC failure: `has_budget=False` and caller still offers add (fail-open).

### Reply composition

Include in bot reply (templates and/or short LLM under a dedicated usage scope):

1. Candidate name, amount, category  
2. If budgeted and not ahead: remaining now + remaining if purchased  
3. If budgeted and ahead: those remainings **plus** pace note  
4. If no budget: clear unlimited / no budget set line  
5. Yes/no ask to add to wish list  

---

## Confirmation pending action

### Module

`services/confirmation_repository.py` + `services/reply_edit.py`

| pending_action | Affirm | Cancel |
| -------------- | ------ | ------ |
| `wish_list_add` | Insert `wish_list_items` from pending payload; reply success | Clear pending; reply cancelled; no insert |

Affirm/cancel detection: existing `is_affirmative` / `is_cancel_pending`.  
No field-edit intents applied to wish pending payload in v1 (user must use web to edit).

---

## Tenant scoping

Use `TenantContext` from the event (`resolve_tenant_from_event`). Group/room chats write wish items to the **shared** ledger.

---

## Non-goals (bot)

- Execute / convert to expense  
- List / reorder / delete wish items  
- Edit fields in chat before add  
