# Contract: Usage Guard Pipeline

**Feature**: 007-llm-usage-limits

## Order of checks (inbound message)

All steps run **before** the first Gemini API call for that inbound message.

| Step | Check | Actor | On failure |
| ---- | ----- | ----- | ---------- |
| 1 | Text word count ≤ 1000 | Sender payload | `payload_too_large_text` |
| 2 | Image bytes ≤ 10 MB | Sender payload | `payload_too_large_image` |
| 3 | Sender LLM messages in last 60s < 10 | Sender | `user_rate_limit_minute` |
| 4 | Sender LLM messages in last 24h < 100 | Sender | `user_rate_limit_day` |
| 5 | Resolve billing user for monthly quota | Sender, then pool | see below |
| 6 | Billing user monthly total < 300 | Billing user | `user_quota_monthly` |
| 7 | If receipt flow: billing user receipt count < 100 | Billing user | `user_receipt_quota_monthly` |

## Billing user resolution (step 5)

```
if sender has required headroom for planned operations:
    billing_user = sender
elif tenant.is_shared:
    donors = tenant_chat_members(exclude sender) with headroom
    if donors empty: DENY user_quota_monthly
    billing_user = random.choice(donors)
else:
    DENY user_quota_monthly
```

**Planned operations** for pre-check: pessimistically assume worst case for message type:
- Text: at least `intent` (+ `assist` if parse fails determinism)
- Image: `intent` optional + `receipt_analysis` + N×`categorize` — pre-check uses **minimum** 1 receipt_analysis + 1 total for gate; per-invocation checks before each call

## Per-invocation re-check

Before each Gemini call in a multi-step flow, verify billing user still has:
- `month_invocations < monthly_total`
- If `operation_type == receipt_analysis`: `month_receipt_analyses < receipt_cap`

If insufficient mid-flow: abort with `user_quota_monthly` or `user_receipt_quota_monthly`; record invocations already completed.

## Message rate counter

Insert into `llm_message_windows` on **first successful** LLM invocation in the flow (after step 7 passes), not on pre-check alone.

## Deterministic parse bypass

If the entire message is handled without calling Gemini, skip steps 3–7 for quota (step 3–4 still skipped per spec: no LLM-backed message).

## Reply-edit flow

Treated as LLM-backed message: sender rate limits apply; billing user = sender in 1:1; pooling allowed in group/room per quota-pooling contract.
