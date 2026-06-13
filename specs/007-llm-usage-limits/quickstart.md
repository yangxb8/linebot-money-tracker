# Quickstart: Per-User LLM Usage Limits

## Prerequisites

- `GEMINI_API_KEY`
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (required for metering persistence)
- Apply migration `supabase/migrations/20260612120000_llm_usage_limits.sql`

## Default free-tier limits

| Limit | Value |
| ----- | ----- |
| Monthly LLM invocations | 300 |
| Monthly receipt analyses | 100 |
| Messages / minute | 10 |
| Messages / day | 100 |
| Max text words | 1,000 |
| Max image size | 10 MB |

Override via env vars (see [contracts/supabase-schema-delta.md](./contracts/supabase-schema-delta.md)).

## Local testing (personal)

```bash
python local_run.py --text "Lunch 1200円"
python local_run.py --image path/to/receipt.jpg
```

Without Supabase, metering is skipped (Gemini still runs). With Supabase, usage rows appear in `llm_usage_events` and `user_usage_summary`.

## Local testing (group pooling)

Simulate two members in the same group:

```bash
# Member A logs expenses until quota exhausted (or use test DB seed)
python local_run.py --group-id "test-group-usage" --text "Lunch 1200円"

# Member B as donor (different LINE user ID)
set LOCAL_LINE_USER_ID=member-b
python local_run.py --group-id "test-group-usage" --image path/to/receipt.jpg
```

Verify in Supabase:
- `tenant_chat_members` has both users for the group tenant
- `llm_usage_events.charged_line_user_id` may be `member-b` when A is over quota
- `llm_usage_events.pooled = true` when donor ≠ sender

## Verify rate limits

Rapid-fire (requires automation or script):

```bash
for /L %i in (1,1,11) do python local_run.py --text "test %i"
```

11th message within a minute should return a rate-limit reply without Gemini call.

## Verify payload limits

```bash
python local_run.py --text "<1001+ word text file contents>"
```

Should reject before LLM.

## SQL spot checks

```sql
-- Current month usage for a user
SELECT * FROM user_usage_summary
WHERE line_user_id = 'your-line-user-id'
ORDER BY jst_year_month DESC;

-- Recent events
SELECT charged_line_user_id, sender_line_user_id, operation_type, pooled, created_at
FROM llm_usage_events
ORDER BY created_at DESC
LIMIT 20;
```

## Distinct error messages

| User limit | Key (i18n) |
| ---------- | ---------- |
| Too fast (minute) | `user_rate_limit_minute` |
| Daily cap | `user_rate_limit_day` |
| Monthly total | `user_quota_monthly` |
| Monthly receipts | `user_receipt_quota_monthly` |
| Text too long | `payload_too_large_text` |
| Image too large | `payload_too_large_image` |
| Provider API 429 | `usage_limit` (existing) |
