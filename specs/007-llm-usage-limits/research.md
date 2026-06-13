# Research: Per-User LLM Usage Limits

**Feature**: 007-llm-usage-limits  
**Date**: 2026-06-12

## R1: Central metering hook point

**Decision**: Wrap `GeminiClient` in `MeteredGeminiClient` that accepts a per-request `UsageBillingContext` (billing user ID, sender ID, operation type, source message ID, idempotency key). Record usage inside `_generate_content_with_retry` only after successful text return.

**Rationale**: LLM calls originate from `intent.py`, `ai_assist.py`, `categorize.py`, `reply_edit.py`, and `message_handler.py` (generate_reply). A single wrapper avoids missing a call site and guarantees one event per logical label success (model retries do not double-bill).

**Alternatives considered**:
- Decorator on each public Gemini method at call sites — error-prone, easy to skip new paths.
- Post-hoc logging in message_handler only — misses mid-flow calls (categorize per item).

---

## R2: Persistence store

**Decision**: Supabase Postgres (existing project) with append-only `llm_usage_events` plus denormalized `user_usage_summary` for fast quota checks.

**Rationale**: Project already uses Supabase for expenses; operator can SQL-audit usage. No new infrastructure (Redis) for v1 household scale.

**Alternatives considered**:
- In-memory counters — lost on Cloud Run cold start; unacceptable.
- Redis sliding windows — lower latency but new dependency; defer until scale demands.

---

## R3: Rolling rate limits (10/min, 100/day)

**Decision**: Table `llm_message_windows` recording one row per **LLM-backed inbound message** (sender, source_message_id unique, created_at). Count rows where `created_at > now() - interval` for minute/day checks. Insert window row on first successful LLM call in the message flow (not on pre-check rejection).

**Rationale**: Spec defines rate limits per sender per message, not per invocation. Unique on `source_message_id` gives idempotent message counting on webhook redelivery.

**Alternatives considered**:
- Count `llm_usage_events` rows — over-counts multi-invocation receipts (one message, 3 LLM calls).
- Token bucket in application memory — not durable across instances.

---

## R4: JST monthly buckets

**Decision**: Store `jst_year_month` as `text` (`YYYY-MM`) on `user_usage_summary`, computed in Python with `zoneinfo.ZoneInfo('Asia/Tokyo')`. On read, if bucket ≠ current JST month, treat monthly counters as zero and upsert new row on first event.

**Rationale**: Matches expense dating (JST). Avoids Postgres timezone surprises in RPCs.

**Alternatives considered**:
- UTC month boundaries — rejected by spec clarification.
- Cron job to reset counters — unnecessary with lazy bucket rollover on write.

---

## R5: Group pool donor discovery

**Decision**: Table `tenant_chat_members(tenant_type, tenant_id, line_user_id, first_seen_at, last_seen_at)` upserted on every inbound message in group/room. Pool query: members in same tenant excluding sender, joined to `user_usage_summary` for headroom.

**Rationale**: Spec requires "prior interactors in that chat" without LINE group membership API. Upsert on handle is O(1) and accurate for bot-known members.

**Alternatives considered**:
- Derive donors from `expenses.logged_by_line_user_id` — misses members who only sent non-expense messages.
- LINE `get_group_members_count` — not available for bot to list all members in v1.

---

## R6: Tier configuration (v1)

**Decision**: `free` tier limits from environment variables with documented defaults; `user_usage_summary.tier` column defaults to `free`. No upgrade API in v1.

**Rationale**: Spec allows deployment configuration without code changes; schema ready for future paid tiers.

**Alternatives considered**:
- `usage_tier_limits` DB table only — harder to change without migration; use env for v1, optional DB seed later.

---

## R7: Quota enforcement under concurrency

**Decision**: Supabase RPC `try_consume_llm_quota(line_user_id, operation_type, amount)` using `UPDATE ... WHERE count + amount <= limit RETURNING` or insert event + recount in transaction. Python retries once on conflict.

**Rationale**: Prevents overdraw when two group messages pool the same donor simultaneously.

**Alternatives considered**:
- Optimistic read-then-write in Python only — race on concurrent donors.
- Pessimistic app lock — no distributed lock service in project.

---

## R8: Limiter behavior when Supabase unavailable

**Decision**: **Fail open on read errors** for usage lookup (log warning, allow message) in local dev without Supabase; **fail closed** in production when `SUPABASE_URL` configured but quota check errors. Payload and word-count checks always run locally.

**Rationale**: Constitution reliability + local `GEMINI_API_KEY`-only workflow. Production must protect cost when DB is intended to be active.

**Alternatives considered**:
- Always fail closed — breaks `local_run.py` without Supabase.
- Always fail open — unacceptable cost risk in production.

---

## R9: Provider vs user limit messaging

**Decision**: Keep existing `GeminiUsageLimitError` → `usage_limit` i18n key for **provider** exhaustion. New keys for **per-user** limits (`user_rate_limit_minute`, `user_rate_limit_day`, `user_quota_monthly`, `user_receipt_quota_monthly`, `payload_too_large`).

**Rationale**: Users need different guidance ("try tomorrow" vs "wait a minute" vs "API quota").

**Alternatives considered**:
- Single generic message — rejected by spec User Story 5.
