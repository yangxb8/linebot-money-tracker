# Data Model: Per-User LLM Usage Limits

**Feature**: 007-llm-usage-limits  
**Extends**: [006 group expenses](../006-group-expenses/spec.md) tenant model

## ERD

```text
user_usage_summary (1 per line_user_id + jst_year_month bucket)
        ▲
        │ aggregates
llm_usage_events (append-only log)

tenant_chat_members (tenant_type, tenant_id, line_user_id)

llm_message_windows (sender rate-limit messages)
```

## Entity: user_usage_summary

Denormalized counters for fast quota enforcement.

| Column | Type | Notes |
| ------ | ---- | ----- |
| line_user_id | text NOT NULL | LINE user |
| jst_year_month | text NOT NULL | `YYYY-MM` in Asia/Tokyo |
| tier | text NOT NULL DEFAULT 'free' | v1 always `free` |
| lifetime_invocations | bigint NOT NULL DEFAULT 0 | Running total (all time) |
| month_invocations | int NOT NULL DEFAULT 0 | Successful LLM calls this JST month |
| month_receipt_analyses | int NOT NULL DEFAULT 0 | Receipt-analysis ops this JST month |
| updated_at | timestamptz NOT NULL DEFAULT now() | |

**Primary key**: `(line_user_id, jst_year_month)`

**Lifetime total**: Either separate row with `jst_year_month = '_lifetime'` or `MAX(lifetime_invocations)` maintained on every write — implementation uses single `_lifetime` pseudo-bucket OR column on latest month row; **preferred**: `lifetime_invocations` updated on every event on the current month row plus optional `user_usage_lifetime` view/RPC.

**Simpler v1 approach**: Store `lifetime_invocations` on a dedicated row `jst_year_month = 'lifetime'` and monthly counters on `YYYY-MM` rows.

## Entity: llm_usage_events

Append-only audit log (FR-001, FR-014).

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | |
| charged_line_user_id | text NOT NULL | Billing user (sender or donor) |
| sender_line_user_id | text NOT NULL | Inbound message sender |
| operation_type | text NOT NULL | `intent`, `receipt_analysis`, `categorize`, `assist`, `reply_edit`, `general` |
| operation_label | text NOT NULL | Gemini label (`intent`, `receipt-image-json`, …) |
| source_message_id | text NULL | LINE inbound message ID |
| tenant_type | text NULL | `user` / `group` / `room` |
| tenant_id | text NULL | |
| pooled | boolean NOT NULL DEFAULT false | True when donor ≠ sender |
| created_at | timestamptz NOT NULL DEFAULT now() | |

**Unique** (idempotency): `(source_message_id, operation_label)` WHERE `source_message_id IS NOT NULL`

## Entity: llm_message_windows

One row per LLM-backed inbound message for sender rate limits.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | |
| sender_line_user_id | text NOT NULL | |
| source_message_id | text NOT NULL UNIQUE | Idempotent per inbound message |
| created_at | timestamptz NOT NULL DEFAULT now() | |

**Index**: `(sender_line_user_id, created_at DESC)` for rolling window counts.

## Entity: tenant_chat_members

Tracks prior interactors per shared tenant for pool eligibility (FR-008a).

| Column | Type | Notes |
| ------ | ---- | ----- |
| tenant_type | text NOT NULL | `group` or `room` |
| tenant_id | text NOT NULL | |
| line_user_id | text NOT NULL | |
| first_seen_at | timestamptz NOT NULL DEFAULT now() | |
| last_seen_at | timestamptz NOT NULL DEFAULT now() | |

**Primary key**: `(tenant_type, tenant_id, line_user_id)`

## Tier limits (configuration, v1)

Not stored per user; read from environment with defaults:

| Tier | monthly_total | monthly_receipt_analysis | rate_minute | rate_day | max_text_words | max_image_bytes |
| ---- | ------------- | ------------------------ | ----------- | -------- | -------------- | --------------- |
| free | 300 | 100 | 10 | 100 | 1000 | 10485760 (10 MB) |

Future: `usage_tier_limits` table keyed by `tier` without changing event schema.

## State transitions

### Quota check (per message flow)

```text
START → payload_ok? → rate_ok(sender)? → quota_ok(sender)?
  → [group & insufficient] → pick_donor → quota_ok(donor)? → ALLOW(billing_user)
  → DENY(localized reason)
```

### Monthly rollover

On write/read, if `jst_year_month != current_jst_yyyy_mm()`:
- Create or use new month row with zero monthly counters
- Lifetime counter continues on `lifetime` row or column

## Validation rules

- `month_receipt_analyses <= month_invocations` always
- `month_invocations <= tier.monthly_total`
- `month_receipt_analyses <= tier.monthly_receipt_analysis`
- Receipt-analysis operation increments both `month_invocations` and `month_receipt_analyses`
- Intent operation increments `month_invocations` only
