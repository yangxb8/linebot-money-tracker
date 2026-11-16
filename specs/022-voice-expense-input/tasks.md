---
description: "Task list for Voice Expense Input feature implementation"
---

# Tasks: Voice Expense Input

**Input**: Design documents from `/specs/022-voice-expense-input/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — FR-011 + constitution Test-First + AGENTS.md suite expansion require unit + `tests/functional/bot/` coverage for happy path, over-duration, over-size, and unusable/non-expense (mocked; no live production ledger).

**Organization**: Tasks grouped by user story (US1 voice expense → US2 abuse limits → US3 unclear audio → US4 harness). Setup/foundation shared before stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Bot: `services/`, `main.py`, `local_run.py`, `tests/` at repository root
- Schema: `supabase/migrations/`
- Functional: `tests/functional/bot/`
- Docs: `docs/ARCHITECTURE.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold modules and i18n placeholders without wiring webhook yet

- [ ] T001 Create `services/audio_limits.py` with `MAX_AUDIO_DURATION_MS = 60_000`, size constant wired to usage config, `AudioLimitViolation` enum, and stub `check_audio_duration` / `check_audio_size` signatures per `contracts/audio-limits.md`
- [ ] T002 [P] Add JA/EN/ZH i18n key placeholders for audio too-long, audio too-large, and unusable audio in `services/confirmation_i18n.py` (and persona variants in `services/persona_i18n.py` if that module mirrors keys)
- [ ] T003 [P] Add empty `process_audio_message` stub (signature only, raises `NotImplementedError` or returns placeholder) in `services/message_handler.py` documenting handoff to text pipeline per `contracts/voice-bot.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, inbound persistence, LINE extract, Gemini audio transcription API, and usage payload checks that ALL stories need

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create Supabase migration `supabase/migrations/YYYYMMDDHHMMSS_inbound_audio_message_type.sql` extending `inbound_messages.message_type` CHECK to include `'audio'` and extending `message_retries.failure_kind` (or equivalent) to include `'audio_fetch_error'` per `contracts/supabase-schema-delta.md`
- [ ] T005 Apply migration to Supabase project `https://nyuenufldaqsjybjhawl.supabase.co` and verify `message_type` CHECK includes `audio` (SQL editor or `supabase db push`)
- [ ] T006 [P] Add `USAGE_MAX_AUDIO_BYTES` (default `5 * 1024 * 1024`) to `services/usage_config.py` and implement `check_payload_audio` in `services/usage_limiter.py`; ensure audio path does **not** trigger receipt-analysis sub-quota
- [ ] T007 [P] Implement `check_audio_duration` / `check_audio_size` (inclusive max; reject strictly greater) in `services/audio_limits.py`
- [ ] T008 [P] Implement `extract_audio_message` in `services/line_event.py` returning `message_id` + optional `duration_ms` when `message.type == "audio"`
- [ ] T009 [P] Implement `save_inbound_audio_message` in `services/inbound_message_repository.py` with `message_type='audio'`
- [ ] T010 Implement Gemini audio content helper(s) in `services/gemini_client.py` (e.g. `generate_text_with_audio` / JSON variant using `Part.from_bytes`, MIME `audio/mp4` or `audio/m4a`) using the **general** model fallback chain
- [ ] T011 [P] Wrap audio Gemini helper in `services/metered_gemini.py` metering as general/assist (**not** `receipt_analysis`)
- [ ] T012 Implement `transcribe_audio` (or equivalent) in `services/ai_assist.py` returning a plain transcript string; empty/whitespace → empty string
- [ ] T013 [P] Add unit tests for duration/size boundary rules in `tests/test_audio_limits.py` (60_000 ms and 5 MiB accepted; +1 rejected)

**Checkpoint**: Foundation ready — migration applied, limits/usage/extract/inbound/Gemini transcription APIs exist and limit unit tests pass

---

## Phase 3: User Story 1 - Log an expense by voice message (Priority: P1) 🎯 MVP

**Goal**: Within-limit LINE voice messages transcribe and produce the same expense confirmation (and ledger rules) as equivalent text

**Independent Test**: Mocked functional webhook with audio event + mocked transcript containing amount → confirmation-style reply and expense insert/confirmation mocks; group context uses group ledger

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US1] Add `audio_message_event` builder (id + optional duration_ms) in `tests/functional/bot/helpers/webhook_events.py`
- [ ] T015 [US1] Add failing functional happy-path skeleton in `tests/functional/bot/test_voice_expense_flow.py` (`bot.voice.expense_confirm`: signed audio webhook → confirmation reply; assert expense/confirmation side effects; mock Gemini transcription + existing parse path; zero live Supabase/LINE)

### Implementation for User Story 1

- [ ] T016 [US1] Implement `process_audio_message` in `services/message_handler.py`: run size check on bytes; call `transcribe_audio`; on non-empty transcript call `process_text_message` with same context/tenant; preserve persona/i18n scope
- [ ] T017 [US1] Wire audio branch in `main.py`: extract audio → (defer over-limit UX to US2 if not yet wired) fetch content via shared blob fetch → `save_inbound_audio_message` → `prepare_inbound_usage` → `process_audio_message` → reply
- [ ] T018 [P] [US1] Generalize image content fetch helper in `main.py` (rename/share) so audio and image use the same `get_message_content` path
- [ ] T019 [US1] Extend `services/message_retry.py` to retry `message_type='audio'` by re-fetching content and calling `process_audio_message`
- [ ] T020 [US1] Complete `bot.voice.expense_confirm` assertions in `tests/functional/bot/test_voice_expense_flow.py` until green; cover multi-item transcript if cheap with existing text mocks
- [ ] T021 [P] [US1] Add unit test that `process_audio_message` delegates to text path with transcript in `tests/test_process_audio_message.py` (mock `transcribe_audio` + `process_text_message`)

**Checkpoint**: US1 MVP — within-limit voice expense confirmation works end-to-end under mocks

---

## Phase 4: User Story 2 - Reject oversized or overly long audio (Priority: P1)

**Goal**: Over-duration / over-size audio is rejected with clear localized messages; no Gemini transcription and no expenses

**Independent Test**: Functional tests for duration &gt; 60s and size &gt; 5 MiB assert rejection reply text includes limits, Gemini not called, no expense inserts

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [P] [US2] Add failing functional case `bot.voice.reject_over_duration` in `tests/functional/bot/test_voice_expense_flow.py` (duration_ms &gt; 60000; prefer no content fetch / no Gemini)
- [ ] T023 [P] [US2] Add failing functional case `bot.voice.reject_over_size` in `tests/functional/bot/test_voice_expense_flow.py` (bytes &gt; 5 MiB; no Gemini; no expense)

### Implementation for User Story 2

- [ ] T024 [US2] Wire duration pre-check in `main.py` (and/or `process_audio_message`) using `check_audio_duration`; on violation reply via i18n too-long key naming **60 seconds**; skip fetch when possible and skip transcription
- [ ] T025 [US2] Wire size check after fetch (and `check_payload_audio` in usage prep) using `check_audio_size`; on violation reply via i18n too-large key naming **5 MB**; skip transcription
- [ ] T026 [US2] Finalize i18n copy in `services/confirmation_i18n.py` / `services/persona_i18n.py` so rejection messages suggest shorter recording or text
- [ ] T027 [US2] Make `bot.voice.reject_over_duration` and `bot.voice.reject_over_size` functional tests green (assert zero transcription/expense mock calls)

**Checkpoint**: US2 — abuse limits enforced with clear UX and functional coverage

---

## Phase 5: User Story 3 - Handle unclear, empty, or non-expense voice (Priority: P2)

**Goal**: Silent/unusable audio and non-expense / wish-intent speech fail gracefully without spurious expenses

**Independent Test**: Empty transcript → retry guidance, no expense; non-expense transcript → existing unsupported path; wish-phrase transcript → wish propose (no expense)

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T028 [P] [US3] Add failing functional/unit cases for empty transcript → unusable reply in `tests/functional/bot/test_voice_expense_flow.py` and/or `tests/test_process_audio_message.py`
- [ ] T029 [P] [US3] Add failing case for wish-intent transcript parity (mocked) in `tests/functional/bot/test_voice_expense_flow.py` (wish propose, no expense insert)

### Implementation for User Story 3

- [ ] T030 [US3] In `process_audio_message` (`services/message_handler.py`), map empty/whitespace transcript and transcription failures to localized unusable-audio reply (no expense)
- [ ] T031 [US3] Confirm non-expense and wish-list transcripts rely on `process_text_message` unchanged; add logging for audio accept → transcript empty vs delegated
- [ ] T032 [US3] Make unusable + wish-intent voice tests green; assert no expense inserts on those paths

**Checkpoint**: US3 — unclear/non-expense/wish voice handled safely

---

## Phase 6: User Story 4 - Local/dev harness voice input (Priority: P3)

**Goal**: `local_run.py --audio` exercises the same pipeline as LINE voice for happy path and over-limit fixtures

**Independent Test**: `python3 local_run.py --audio path/to/sample.m4a` prints confirmation-class reply (with `GEMINI_API_KEY`); oversize/overlong fixtures print rejection replies

### Tests for User Story 4

- [ ] T033 [P] [US4] Add a lightweight unit/harness test or argparse smoke asserting `--audio` is accepted in `tests/test_local_run_audio.py` (or extend existing local_run tests) without requiring live Gemini when mocked

### Implementation for User Story 4

- [ ] T034 [US4] Add `--audio` argument and file read helper in `local_run.py` parallel to `--image`; call `save_inbound_audio_message` + `process_audio_message` with duration from optional probe or `None`
- [ ] T035 [US4] Support over-limit fixtures via large file and/or injectable duration in harness path so quickstart abuse checks work
- [ ] T036 [P] [US4] Document sample commands already in `specs/022-voice-expense-input/quickstart.md`; fix any drift discovered while wiring `--audio`

**Checkpoint**: US4 — console harness supports voice like text/image

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Architecture sync, suite green, docs consistency

- [ ] T037 [P] Update `docs/ARCHITECTURE.md` expense-capture / inbound flows to include voice/audio beside text and image (architecture-docs gate)
- [ ] T038 [P] Update `AGENTS.md` Cursor Cloud bot run notes to mention `python3 local_run.py --audio ...` and 60s/5MB limits if not already covered via specify-rules alone
- [ ] T039 Run `python3 -m pytest -q tests/test_audio_limits.py tests/test_process_audio_message.py tests/functional/bot/test_voice_expense_flow.py` and fix failures
- [ ] T040 Run full `python3 -m pytest -q` (bot suite including functional) and ensure no regressions
- [ ] T041 Verify quickstart paths in `specs/022-voice-expense-input/quickstart.md` against implemented flags/messages; mark spec status Implemented when done
- [ ] T042 [P] Confirm `.cursor/rules/specify-rules.mdc` still points at `specs/022-voice-expense-input/plan.md` and `--audio` quickstart note

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP
- **US2 (Phase 4)**: Depends on Foundational; can proceed in parallel with US1 after T013, but webhook reject wiring should land before calling US1 “done” in production
- **US3 (Phase 5)**: Depends on US1 `process_audio_message` + text delegation
- **US4 (Phase 6)**: Depends on US1 handler (and ideally US2 reject paths)
- **Polish (Phase 7)**: Depends on desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on US3/US4
- **US2 (P1)**: After Foundational limit APIs — independently testable via reject functional tests
- **US3 (P2)**: After US1 transcription → text handoff exists
- **US4 (P3)**: After US1 (harness calls same handler); better after US2 for over-limit demos

### Within Each User Story

- Tests marked first MUST fail before implementation where noted
- Handler before webhook polish
- Functional green before story checkpoint

### Parallel Opportunities

- T002/T003 after T001 scaffold
- T006–T009, T011, T013 in Foundational once migration drafted
- T014/T015 (US1 tests) parallel
- T022/T023 (US2 tests) parallel
- T028/T029 (US3 tests) parallel
- T037/T038/T042 polish docs in parallel

---

## Parallel Example: User Story 1

```bash
# Tests first (parallel):
Task: "Add audio_message_event in tests/functional/bot/helpers/webhook_events.py"
Task: "Add failing bot.voice.expense_confirm in tests/functional/bot/test_voice_expense_flow.py"

# Then implementation:
Task: "Implement process_audio_message in services/message_handler.py"
Task: "Wire audio branch + shared content fetch in main.py"
Task: "Extend message_retry.py for audio"
```

---

## Parallel Example: User Story 2

```bash
Task: "Add bot.voice.reject_over_duration functional case"
Task: "Add bot.voice.reject_over_size functional case"
# Then wire main.py / process_audio_message reject replies + i18n copy
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup  
2. Complete Phase 2: Foundational  
3. Complete Phase 3: US1 (include minimal within-limit path; land US2 reject wiring before production expose)  
4. **STOP and VALIDATE**: `pytest` functional happy path green  
5. Demo via harness once US4 lands, or mocked functional alone

### Incremental Delivery

1. Setup + Foundational → APIs ready  
2. US1 → voice expense confirm (MVP)  
3. US2 → abuse-limit rejects (ship-critical with US1)  
4. US3 → unusable / wish parity  
5. US4 → `--audio` harness  
6. Polish → architecture + full suite green  

### Suggested MVP Scope

**US1 + US2** (both P1): voice expense logging with abuse limits. US3/US4 follow immediately in the same implementation PR preferred so FR-011 and harness acceptance are met before merge.

---

## Notes

- [P] = different files, no incomplete-task dependencies  
- Do not persist long-term audio blobs (out of scope)  
- Do not add web mic UI  
- Voice reply-edit is out of scope (text replies only)  
- Apply Supabase migration before relying on inbound audio rows in shared environments  
- Commit after each task or logical group  
