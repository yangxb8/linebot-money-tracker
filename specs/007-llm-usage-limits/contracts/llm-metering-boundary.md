# Contract: LLM Metering Boundary

**Feature**: 007-llm-usage-limits

## Rule

All production Gemini access MUST go through `MeteredGeminiClient` when usage limits are enabled (`SUPABASE_URL` configured).

## UsageBillingContext (per inbound message flow)

```python
@dataclass(frozen=True)
class UsageBillingContext:
    billing_line_user_id: str      # sender or pooled donor; fixed for flow
    sender_line_user_id: str
    source_message_id: Optional[str]
    tenant_type: Optional[str]
    tenant_id: Optional[str]
    pooled: bool
    message_window_recorded: bool  # mutable flag: first success sets True
```

Passed from `message_handler` / `reply_edit` into every metered Gemini call.

## Operation type mapping

| GeminiClient method | label | operation_type | Counts receipt cap |
| ------------------- | ----- | -------------- | ------------------ |
| `generate_json_reply` (intent) | intent | intent | No |
| `generate_json_reply_with_image` (receipt) | receipt-image-json | receipt_analysis | Yes |
| `generate_json_reply` (categorize, assist, edit) | json | categorize / assist / reply_edit | No |
| `generate_reply` | text | general | No |

Map `json` label to specific `operation_type` via caller-provided override on context.

## On success

1. If not `message_window_recorded`: insert `llm_message_windows` for sender; set flag.
2. Insert `llm_usage_events` (idempotent on source_message_id + operation_label).
3. Increment `user_usage_summary` for `billing_line_user_id` current JST month (+ lifetime).

## On failure

- Gemini exception before success text: **no** event, **no** counter increment.
- Model fallback retries within same label: **one** event on first success only.

## On provider quota (429)

Raise `GeminiUsageLimitError` — **no** user quota consumed. Return existing provider `usage_limit` i18n message.

## Local dev without Supabase

`MeteredGeminiClient` delegates without recording when `is_supabase_configured()` is false.
