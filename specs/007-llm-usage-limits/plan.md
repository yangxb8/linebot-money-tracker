# Implementation Plan: Per-User LLM Usage Limits

**Branch**: `007-llm-usage-limits` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification + clarifications (free tier 300/month + 100 receipt analyses, group pooling, sender rate limits / donor quota, intent checks billable). Builds on **006-group-expenses**.

## Summary

Add **per-user LLM metering and enforcement** before and around every Gemini call: payload guards (1,000 words / 10 MB), sender rate limits (10/min, 100/day rolling), free-tier monthly caps (300 invocations, 100 receipt analyses), durable usage logging in Supabase, and **group quota pooling** from prior interactors in the same chat. Centralize checks in a `usage_limiter` service; wrap `GeminiClient` to record successful invocations against the resolved billing user (sender or pooled donor).

## Technical Context

**Language/Version**: Python 3.11+ (3.13 in CI)

**Primary Dependencies**: FastAPI, line-bot-sdk, google-genai, supabase, pytest (unchanged)

**Storage**: Supabase Postgres — new tables `llm_usage_events`, `user_usage_summary`, `llm_message_windows`, `tenant_chat_members`; optional `usage_tier_limits` seed row for `free` (or env-driven defaults)

**Testing**: pytest with mocked Supabase + Gemini; unit tests for limiter, pooling selection, JST month rollover, idempotent billing; handler integration tests for rejection paths

**Target Platform**: Google Cloud Run + `local_run.py` (limiter active when Supabase configured; env-only tier defaults when not)

**Project Type**: web-service + CLI dev harness

**Performance Goals**: Pre-check path (payload + rate + quota) ≤50ms p95 when Supabase warm; limiter must not add >100ms p95 to webhook excluding LLM

**Constraints**:
- Checks run **before** first LLM call per inbound message (FR-010/011)
- One usage event per logical Gemini label success, not per model retry (spec edge case)
- Idempotent on `(source_message_id, operation_label)` when message ID present
- Sender always owns rate-limit counters; billing user may differ under pooling
- Provider `GeminiUsageLimitError` (API 429) remains separate from per-user limits
- Tier limits configurable via env without code change in v1

**Scale/Scope**: Small household groups (<20 prior interactors); thousands of usage events/month per active user; no admin UI in v1

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | New `usage_limiter.py`, `usage_repository.py`, `metered_gemini.py` (wrapper); single enforcement entry point |
| Test-First Delivery | Tests for each limit type, pooling, idempotency, JST buckets, localized denial messages |
| User Experience Consistency | Distinct JA/EN/ZH messages per limit type in `confirmation_i18n` or `usage_limit_i18n` |
| Performance & Reliability | Pre-check fail-fast; DB failures on metering log warning but do not block expense flow (configurable fail-open for read path only — **fail closed on quota when DB available**) |
| Observability & Feedback | Append-only `llm_usage_events`; structured logs with `charged_user`, `sender`, `operation`, `pool_donor` |
| Secrets | Unchanged — service role server-only |

**Post-design re-check**: PASS

## Architecture

```text
┌──────────────┐  inbound        ┌──────────────────┐  pre-checks      ┌─────────────┐
│ LINE webhook │ ──────────────► │ main.py          │ ───────────────► │usage_limiter│
│ / local_run  │                 │ message_handler  │                  │ payload     │
└──────────────┘                 └────────┬─────────┘                  │ rate (sender│
                                          │                            │ quota/pool) │
                                          ▼                            └──────┬──────┘
                                 ┌──────────────────┐                          │
                                 │ MeteredGemini    │ ◄── UsageContext ────────┘
                                 │ (wraps Client)   │     (billing user locked
                                 └────────┬─────────┘      per message flow)
                                          │ success
                                          ▼
                                 ┌──────────────────┐
                                 │ usage_repository │ ──► Supabase
                                 │ record_event     │
                                 └──────────────────┘
```

### Request flow

1. **Payload check** on raw text length (words) or image bytes size — no DB required.
2. **Rate check** on sender using rolling counts from `llm_message_windows` (or event query).
3. **Quota resolve** — sender first; if group/room and insufficient, pick random eligible donor from `tenant_chat_members` with headroom for operation type (total + receipt sub-cap when applicable).
4. Lock **billing user** on `UsageContext` for entire message processing flow.
5. On first LLM invocation in flow, increment sender **message** rate counter (one per inbound message).
6. Each successful `GeminiClient` call through wrapper records one `llm_usage_events` row and bumps `user_usage_summary`.

### LLM operation labels (metered)

| Label | Operation type | Receipt sub-cap |
| ----- | -------------- | --------------- |
| `intent` | intent | No |
| `receipt-image-json` | receipt_analysis | Yes |
| `json` (categorize, assist_parse_text, reply-edit) | categorize / assist / reply_edit | No |
| `text` (generate_reply fallback) | general | No |

## Project Structure

### Documentation (this feature)

```text
specs/007-llm-usage-limits/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── usage-guard-pipeline.md
    ├── llm-metering-boundary.md
    ├── quota-pooling.md
    └── supabase-schema-delta.md
```

### Source Code (repository root)

```text
services/
  usage_limiter.py           # NEW: pre-checks, pool resolution, UsageContext
  usage_repository.py        # NEW: Supabase read/write for usage + members
  metered_gemini.py          # NEW: GeminiClient wrapper records on success
  usage_limit_i18n.py        # NEW: localized limit denial messages
  gemini_client.py             # unchanged core; called via wrapper
  message_handler.py           # wire UsageContext; payload checks on image path
  main.py                      # build UsageContext from event; upsert tenant member
  tenant_context.py            # expose tenant for pool queries
supabase/migrations/
  20260612120000_llm_usage_limits.sql
tests/
  test_usage_limiter.py
  test_usage_repository.py
  test_metered_gemini.py
  test_message_handler_usage.py
local_run.py                   # optional --skip-usage-limits for offline dev
```

**Structure Decision**: Single Python service layout; metering as cross-cutting wrapper rather than editing every call site.

## Implementation Approach

### Phase A — Schema & repository (P1)

1. Migration: tables + indexes (see [data-model.md](./data-model.md)).
2. `usage_repository`: get/increment summary, append event, idempotent insert, list pool donors, upsert tenant member.
3. Env config: `USAGE_TIER_FREE_MONTHLY_TOTAL=300`, `USAGE_TIER_FREE_RECEIPT_MONTHLY=100`, rate limits, payload caps.

### Phase B — Limiter & wrapper (P1)

1. `usage_limiter.check_inbound_message(...)` → `LimitCheckResult` (allow | deny + reason).
2. `usage_limiter.resolve_billing_user(...)` for quota pool.
3. `MeteredGeminiClient` delegates to `GeminiClient`; on success calls `record_invocation`.
4. Replace `gemini_client` injection in `main.py` / handlers with metered wrapper when Supabase configured.

### Phase C — Handler integration (P1)

1. `main.py`: upsert `tenant_chat_members` on each message; run pre-check before `process_*`.
2. `process_text_message` / `process_image_message` / `process_reply_edit`: accept `UsageContext`.
3. Word count on text; byte size on image before download processing where possible.

### Phase D — Group pooling (P2)

1. Query donors: same `(tenant_type, tenant_id)`, exclude sender, `last_seen_at` proves prior interaction.
2. Filter by required headroom; `random.choice` among eligible.
3. Integration tests with two `LOCAL_LINE_USER_ID` values in `--group-id`.

### Phase E — i18n & polish (P2)

1. Localized messages: payload too large, rate minute, rate day, monthly total, receipt monthly.
2. Distinguish user limit vs provider `GeminiUsageLimitError` message.

## Complexity Tracking

No constitution violations requiring justification.
