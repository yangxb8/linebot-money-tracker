# Monthly Report Bot Contract

**Feature**: 022-monthly-expense-report  
**Type**: Internal Python service + webhook integration

## Intent classification

### Module

`services/intent.py`

### Change

`TextMessageIntent = Literal['expense', 'webapp', 'wish_list', 'monthly_report', 'other']`

`COMBINED_TEXT_INTENT_PROMPT` adds:

- `monthly_report`: user wants a period spending/budget summary report image (e.g. “monthly report”, “レポート見せて”, “先月のまとめ”, “家計レポート”, “show my budget report”).
- Prefer `monthly_report` when clearly asking for a report/summary of a period’s spending vs budget, not logging a purchase or wish.

Deterministic phrase gate MAY short-circuit obvious report phrases before LLM.

### Function

`classify_text_message_intent(text, gemini) -> TextMessageIntent`  
Must accept/return `monthly_report`.

---

## Message handling

### Module

`services/message_handler.py`

### Period tip (all text/image primary replies)

Before or after building the primary reply for an inbound message (not tip-only turns):

1. Resolve current fiscal `period_start` for the conversation tenant.
2. If no row in `monthly_report_tips` for `(tenant, period_start)`, and this is the first handled message of that period for the conversation, append/prepend tip text (i18n/persona).
3. Upsert tip row so later messages (including other group members) do not tip again.
4. Tip MUST NOT create/start a report artifact.

If the message intent is `monthly_report`, report flow takes precedence (tip may be omitted or folded into caption/ack).

### Text path — `monthly_report`

| Condition | Behavior |
| --------- | -------- |
| Resolve period (default previous completed; named current/past) | Invalid/future → clear text error; no image |
| Artifact ready + fingerprint match | Reply with image (+ short caption); no expense/wish writes |
| Artifact preparing | In-progress text; invite ask again |
| Artifact missing/failed/stale | Start prepare; same-turn image if ready within ~8s; else preparing text and finish in background |

### Image path

Inbound receipt/item images do **not** map to `monthly_report` (no image-only report ask in v1).

---

## BotReply extension

### Module

`services/message_context.py`

```text
BotReply:
  text: str
  confirmation: Optional[...]
  retryable_failure: Optional[str]
  image: Optional[ReportImagePayload]   # NEW
```

`ReportImagePayload`:
- `original_url: str` (HTTPS, for LINE)
- `preview_url: str` (HTTPS, ≤1MB guidance)
- Optional harness: `local_path` / bytes for `local_run.py`

### `main.py`

When `bot_reply.image` is set, `reply_message` includes:

1. Optional `TextMessage` with `bot_reply.text` (caption / ack)
2. `ImageMessage` with `original_content_url` + `preview_image_url`

When only text (preparing/tip/error), keep today’s text-only reply.

### `local_run.py`

On image payload: write/copy PNG to a visible path and print it; print caption text.

---

## i18n keys (minimum)

| Key | Purpose |
| --- | ------- |
| `monthly_report_tip` | New-period tip (report available when you ask) |
| `monthly_report_preparing` | Preparing; ask again to receive |
| `monthly_report_in_progress` | Still preparing |
| `monthly_report_failed` | Failed; ask again later |
| `monthly_report_caption` | Short caption with period label |
| `monthly_report_future` | Future period not allowed |
| `monthly_report_empty_budgetless` | No spend / no budget framing helpers as needed |

All keys MUST go through persona/i18n resolution like other bot copy.
