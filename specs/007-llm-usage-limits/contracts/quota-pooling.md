# Contract: Group Quota Pooling

**Feature**: 007-llm-usage-limits

## Eligibility

| Condition | Required |
| --------- | -------- |
| Tenant | `tenant_type` ∈ `{group, room}` |
| Sender monthly headroom | Insufficient for pending operation |
| Donor set | Rows in `tenant_chat_members` for same `(tenant_type, tenant_id)`, `line_user_id != sender` |
| Donor headroom | `month_invocations < 300` AND (if receipt) `month_receipt_analyses < 100` |
| Sender rate limits | Under 10/min and 100/day (always checked on sender) |

## Selection

```python
eligible = [d for d in donors if has_headroom(d, operation_need)]
billing_user = random.choice(eligible)  # uniform
```

If `eligible` is empty → deny with `user_quota_monthly` or `user_receipt_quota_monthly` as appropriate.

## Charging

- All LLM invocations in the message flow charge `billing_user` (donor).
- `llm_usage_events.pooled = true`, `sender_line_user_id` remains original sender.
- Donor's `month_receipt_analyses` increments on receipt-analysis ops.

## Receipt pooling

When sender exhausted receipt sub-cap but has total headroom:
- Pooling allowed if donor has **both** caps available.
- If donors have total headroom but no receipt headroom → `user_receipt_quota_monthly`.

## 1:1 chats

Pooling disabled. Sender must have personal headroom or request denied.

## Privacy

Do not disclose donor identity in bot replies (spec out of scope).

## Member discovery

Upsert `tenant_chat_members` on every inbound message in group/room before limit checks so sender is registered for future donation.
