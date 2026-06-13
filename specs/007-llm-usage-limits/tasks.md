# Tasks: Per-User LLM Usage Limits

**Input**: Design documents from `/specs/007-llm-usage-limits/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; **006-group-expenses** on branch baseline

**Organization**: Tasks grouped by user story. **MVP = Phase 1–2 + User Stories 1–3** (tracking, payload guards, rate limits).

**Tests**: Included per constitution Test-First Delivery and plan.md testing strategy.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to spec user stories (US1–US5)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Shared types, tier configuration, and module scaffolding

- [X] T001 [P] Add `UsageBillingContext` dataclass to `services/message_context.py` per `specs/007-llm-usage-limits/contracts/llm-metering-boundary.md`
- [X] T002 [P] Create `services/usage_config.py` reading free-tier limits from env (`USAGE_TIER_FREE_MONTHLY_TOTAL`, `USAGE_TIER_FREE_RECEIPT_MONTHLY`, `USAGE_RATE_LIMIT_PER_MINUTE`, `USAGE_RATE_LIMIT_PER_DAY`, `USAGE_MAX_TEXT_WORDS`, `USAGE_MAX_IMAGE_BYTES`) with spec defaults per `specs/007-llm-usage-limits/contracts/supabase-schema-delta.md`
- [X] T003 [P] Create stub `services/usage_limiter.py` with `LimitCheckResult` and `LimitDenyReason` enum aligned to `specs/007-llm-usage-limits/contracts/usage-guard-pipeline.md`
- [X] T004 [P] Create stub `services/usage_repository.py` with `is_usage_tracking_enabled()` mirroring `is_supabase_configured()` pattern from `services/expense_repository.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, repository core, metered Gemini wrapper skeleton — MUST complete before user story phases

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create `supabase/migrations/20260612120000_llm_usage_limits.sql` with tables `user_usage_summary`, `llm_usage_events`, `llm_message_windows`, `tenant_chat_members` per `specs/007-llm-usage-limits/contracts/supabase-schema-delta.md`
- [X] T006 Apply migration to `https://nyuenufldaqsjybjhawl.supabase.co` via Supabase MCP `apply_migration`; verify with `list_tables`
- [X] T007 [P] Implement JST month bucket helper (`current_jst_year_month()`) in `services/usage_repository.py` per `specs/007-llm-usage-limits/research.md` R4
- [X] T008 [P] Implement `upsert_tenant_chat_member(tenant, line_user_id)` in `services/usage_repository.py` per `specs/007-llm-usage-limits/data-model.md`
- [X] T009 [P] Create stub `services/metered_gemini.py` wrapping `GeminiClient` and delegating all public methods per `specs/007-llm-usage-limits/plan.md`
- [X] T010 [P] Add unit tests for `usage_config` defaults and JST bucket helper in `tests/test_usage_config.py`

**Checkpoint**: Migration live; repository stubs callable; config loads from env

---

## Phase 3: User Story 1 - Per-user usage tracking (Priority: P1) 🎯 MVP

**Goal**: Every successful LLM invocation attributed to a LINE user with lifetime and JST monthly counters in Supabase

**Independent Test**: Process expense messages triggering LLM calls; verify `llm_usage_events` rows and `user_usage_summary` lifetime/month counts match successful invocations; JST month rollover resets monthly counters only

### Tests for User Story 1

- [X] T011 [P] [US1] Add unit tests for idempotent `record_llm_usage` on `(source_message_id, operation_label)` in `tests/test_usage_repository.py`
- [X] T012 [P] [US1] Add unit tests for `MeteredGeminiClient` recording one event per label success (not per model retry) in `tests/test_metered_gemini.py`

### Implementation for User Story 1

- [X] T013 [US1] Implement `record_llm_usage()` and `get_user_usage_summary()` in `services/usage_repository.py` per `specs/007-llm-usage-limits/data-model.md`
- [X] T014 [US1] Implement success-path metering in `services/metered_gemini.py`: append `llm_usage_events`, increment `user_usage_summary` (total + receipt sub-counter when `operation_type=receipt_analysis`) per `specs/007-llm-usage-limits/contracts/llm-metering-boundary.md`
- [X] T015 [US1] Map Gemini labels to `operation_type` in `services/metered_gemini.py` (`intent`, `receipt_analysis`, `categorize`, `assist`, `reply_edit`, `general`)
- [X] T016 [US1] Wire `MeteredGeminiClient` into `main.py` (replace raw `GeminiClient` when usage tracking enabled) and pass through to `message_handler` / `reply_edit` call chains

**Checkpoint**: Successful Gemini calls persist usage rows; failed calls do not

---

## Phase 4: User Story 2 - Payload size limits (Priority: P1) 🎯 MVP

**Goal**: Reject text >1,000 words and images >10 MB before any LLM call with localized denial

**Independent Test**: Send oversized text/image via `local_run.py`; confirm rejection reply and zero new `llm_usage_events` rows

### Tests for User Story 2

- [X] T017 [P] [US2] Add unit tests for word-count and byte-size validation in `tests/test_usage_limiter.py`

### Implementation for User Story 2

- [X] T018 [P] [US2] Create `services/usage_limit_i18n.py` with `payload_too_large_text` and `payload_too_large_image` strings (JA/EN/ZH)
- [X] T019 [US2] Implement `check_payload_text()` and `check_payload_image()` in `services/usage_limiter.py` per FR-003/FR-004
- [X] T020 [US2] Call payload checks in `main.py` before `process_text_message` / `process_image_message` and return denial reply without invoking handlers when failed

**Checkpoint**: Oversize inputs blocked pre-LLM with no usage increment

---

## Phase 5: User Story 3 - Multi-level message rate limits (Priority: P1) 🎯 MVP

**Goal**: Enforce 10 LLM-backed messages per sender per 60s and 100 per 24h rolling windows

**Independent Test**: Rapid-fire 11 LLM-backed messages within a minute; 11th rejected without Gemini call; deterministic parse path does not increment rate counters

### Tests for User Story 3

- [X] T021 [P] [US3] Add unit tests for rolling minute/day counts and idempotent `llm_message_windows` insert in `tests/test_usage_limiter.py`

### Implementation for User Story 3

- [X] T022 [US3] Implement `count_sender_messages_in_window()` and `record_llm_backed_message()` in `services/usage_repository.py` using `llm_message_windows`
- [X] T023 [US3] Implement `check_sender_rate_limits()` in `services/usage_limiter.py` per FR-005/FR-006 (sender only)
- [X] T024 [US3] Integrate rate-limit pre-check in `main.py` before first LLM call; record message window on first successful invocation via `MeteredGeminiClient` per `specs/007-llm-usage-limits/contracts/usage-guard-pipeline.md`
- [X] T025 [US3] Ensure deterministic-only text parse path skips rate/quota checks when no Gemini invoked in `services/message_handler.py`

**Checkpoint**: Rate limits enforced on sender; multi-invocation receipt counts as one message

---

## Phase 6: User Story 4 - Group quota pooling (Priority: P2)

**Goal**: When sender lacks monthly quota (total or receipt sub-cap), charge a random eligible prior interactor in the same group/room

**Independent Test**: Exhaust user A quota in `--group-id` chat; send receipt from A while B has headroom; verify `llm_usage_events.charged_line_user_id=B` and `pooled=true`

### Tests for User Story 4

- [X] T026 [P] [US4] Add unit tests for donor eligibility, random selection, receipt sub-cap headroom, and sender rate-limit blocking before pool in `tests/test_usage_limiter.py`

### Implementation for User Story 4

- [X] T027 [US4] Implement `list_eligible_donors(tenant, sender, need_receipt_headroom)` in `services/usage_repository.py` per `specs/007-llm-usage-limits/contracts/quota-pooling.md`
- [X] T028 [US4] Implement `resolve_billing_user()` with random donor selection in `services/usage_limiter.py` per FR-008/FR-008a/FR-008b
- [X] T029 [US4] Upsert `tenant_chat_members` on every inbound group/room message in `main.py` before limit checks
- [X] T030 [US4] Lock `UsageBillingContext.billing_line_user_id` for entire message flow in `services/message_handler.py` and `services/reply_edit.py` (pooling applies to reply-edits in shared tenants)
- [X] T031 [US4] Add per-invocation quota re-check before each Gemini call in `services/metered_gemini.py` for mid-flow exhaustion

**Checkpoint**: Group pooling charges donor; 1:1 never pools

---

## Phase 7: User Story 5 - Clear limit feedback (Priority: P2)

**Goal**: Distinct localized replies for each limit type (payload, rate minute/day, monthly total, receipt monthly) separate from provider `GeminiUsageLimitError`

**Independent Test**: Trigger each limit type; verify distinct JA/EN/ZH message keys

### Tests for User Story 5

- [X] T032 [P] [US5] Add unit tests for all `usage_limit_i18n` keys and denial reason mapping in `tests/test_usage_limit_i18n.py`

### Implementation for User Story 5

- [X] T033 [P] [US5] Add `user_rate_limit_minute`, `user_rate_limit_day`, `user_quota_monthly`, `user_receipt_quota_monthly` strings to `services/usage_limit_i18n.py` (JA/EN/ZH)
- [X] T034 [US5] Map `LimitDenyReason` → i18n reply in `services/usage_limiter.py` `format_denial_reply(language, reason)`
- [X] T035 [US5] Return denial replies from `main.py` for each pre-check failure using sender's `reply_language`; keep existing `usage_limit` key for provider `GeminiUsageLimitError` only

**Checkpoint**: Users see specific guidance per limit type

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integration tests, env docs, quickstart validation

- [X] T036 [P] Add handler integration tests for pre-check denial paths in `tests/test_message_handler_usage.py`
- [X] T037 [P] Document new env vars in `specs/003-local-dev-setup/contracts/environment-variables.md`
- [X] T038 Wire optional `--skip-usage-limits` flag in `local_run.py` for offline dev without Supabase
- [X] T039 Run `specs/007-llm-usage-limits/quickstart.md` scenarios (personal, group pooling spot-check, payload rejection) and fix gaps
- [X] T040 Implement fail-closed on quota check errors when Supabase configured vs fail-open when not per `specs/007-llm-usage-limits/research.md` R8 in `services/usage_limiter.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS** all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — metering foundation for all later stories
- **US2 (Phase 4)**: Depends on Phase 2; integrates with Phase 3 wiring in `main.py` (T020 after T016)
- **US3 (Phase 5)**: Depends on Phase 2–3 (message window recording in metered client)
- **US4 (Phase 6)**: Depends on Phase 3 (usage summary) + Phase 2 (`tenant_chat_members`)
- **US5 (Phase 7)**: Depends on US2–US4 denial reasons being defined; can parallelize i18n strings (T033) early
- **Polish (Phase 8)**: Depends on desired user stories complete

### User Story Dependencies

| Story | Depends on | Independent test |
| ----- | ---------- | ---------------- |
| US1 | Foundational | Usage rows after LLM success |
| US2 | Foundational | Oversize rejection, no events |
| US3 | US1 (message window on first success) | 11th message/min blocked |
| US4 | US1 + tenant members | Pooled `charged_line_user_id` |
| US5 | US2–US4 reasons | Distinct denial messages |

### Parallel Opportunities

- Phase 1: T001–T004 all [P]
- Phase 2: T007–T010 [P] after T005 migration file exists
- Within US1: T011–T012 [P], then T013–T015 sequential
- US2 T018 [P] parallel with US1 late tasks if different authors
- US5 T033 [P] can start once denial enum exists (T003)

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
tests/test_usage_repository.py
tests/test_metered_gemini.py

# Then sequential:
services/usage_repository.py → services/metered_gemini.py → main.py wiring
```

## Parallel Example: User Story 4

```bash
# After US1 complete:
tests/test_usage_limiter.py  # pool tests
services/usage_repository.py  # list_eligible_donors
services/usage_limiter.py  # resolve_billing_user
main.py  # tenant member upsert
```

---

## Implementation Strategy

### MVP First (User Stories 1–3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 — usage tracking
4. Complete Phase 4: US2 — payload guards
5. Complete Phase 5: US3 — rate limits
6. **STOP and VALIDATE** per `specs/007-llm-usage-limits/quickstart.md`
7. Deploy — cost protection live without group pooling

### Incremental Delivery

1. Setup + Foundational → schema ready
2. US1 → metering visible in Supabase
3. US2 + US3 → full pre-LLM guardrails (MVP)
4. US4 → group pooling
5. US5 → polished denial copy
6. Polish → docs and integration tests

### Suggested MVP Scope

**Phases 1–5 (T001–T025)**: Tracking + payload + rate limits — satisfies P1 stories and SC-001–SC-004, SC-006–SC-007.

---

## Notes

- Quota pre-check (monthly 300 / receipt 100) spans US1 + US4; basic sender-only quota deny can ship in US1 T014/T016; pooling in US4
- Intent-check billing per clarification: counts toward total quota + rate limits, not receipt sub-cap
- Provider `GeminiUsageLimitError` remains separate from per-user limits (US5 T035)
- Commit after each phase checkpoint
