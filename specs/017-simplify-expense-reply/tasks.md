# Tasks: Simplify LINE expense confirmation replies

**Input**: Design documents from `specs/017-simplify-expense-reply/`

**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`

**Tests**: Included (required by constitution “Test-First Delivery” for user-facing behavior).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm baseline test harness + identify existing formatting call sites

- [ ] T001 Inventory current confirmation formatting entry points in `services/message_handler.py` and `services/confirmation_i18n.py`
- [ ] T002 [P] Add/extend test fixtures for sample expenses (single + multi-item) in `tests/` for confirmation formatting
- [ ] T003 [P] Document the new reply formats in `specs/017-simplify-expense-reply/contracts/reply-composition.md` examples (keep in sync during implementation)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core reply composer abstraction + settings plumbing scaffolding

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create a reply composer module for confirmation replies in `services/reply_composer.py`
- [ ] T005 [P] Define a minimal “confirmation display preference” interface in `services/tenant_settings.py` or a new helper `services/confirmation_display_settings.py`
- [ ] T006 Add contract-level unit tests for section joining and separator rules in `tests/test_reply_composer.py`
- [ ] T007 Wire the composer into the existing confirmation reply path in `services/message_handler.py` (behind a feature flag or default-on switch as decided in implementation)

**Checkpoint**: Foundation ready — composer exists, is unit-tested, and is called from the confirmation path

---

## Phase 3: User Story 1 - Receipt-style confirmation for single-item expenses (Priority: P1) 🎯 MVP

**Goal**: Single-item confirmations become one compact receipt line (no instruction block), while preserving optional warning sections.

**Independent Test**: Submit a single-item expense via the text pipeline and assert the reply matches the compact pattern and excludes the long instructions block.

### Tests for User Story 1

- [ ] T008 [P] [US1] Add unit tests for compact single-item rendering in `tests/test_confirmation_i18n.py` (or new `tests/test_confirmation_compact.py`)
- [ ] T009 [P] [US1] Add integration-level tests for `process_text_message()` confirmation output in `tests/test_message_handler_reply.py`

### Implementation for User Story 1

- [ ] T010 [US1] Implement compact single-item summary format in `services/reply_composer.py`
- [ ] T011 [US1] Remove always-on instruction paragraph from confirmation output (ensure help still available via US4) in `services/confirmation_i18n.py` or composer layer
- [ ] T012 [US1] Ensure budget pace warning (if present) remains a distinct short section before the compact summary in `services/budget_pace.py` integration point

**Checkpoint**: US1 complete — single-item confirmations are compact and tests prove no instruction wall-of-text appears

---

## Phase 4: User Story 2 - Category correction via natural-language reply (Priority: P1)

**Goal**: Users can reply with a category phrase; if it’s not an exact match, bot guesses and requires explicit `YES` confirmation (no numbered alternatives by default).

**Independent Test**: Reply-edit with a non-exact category input triggers a `YES` confirmation prompt; replying `YES` applies the edit; non-YES does not apply.

### Tests for User Story 2

- [ ] T013 [P] [US2] Add tests for the `YES` confirmation prompt copy and behavior in `tests/test_reply_edit.py`
- [ ] T014 [P] [US2] Add tests for “no apply without YES” safety in `tests/test_reply_edit.py`

### Implementation for User Story 2

- [ ] T015 [US2] Implement `YES` confirmation prompt formatting per `specs/017-simplify-expense-reply/contracts/category-confirmation.md` in `services/reply_summary.py` (or a new helper)
- [ ] T016 [US2] Update reply-edit intent/application path to require explicit `YES` before applying guessed-category edits (where applicable) in `services/reply_edit.py`

**Checkpoint**: US2 complete — category mismatch requires `YES` confirmation and is covered by tests

---

## Phase 5: User Story 3 - Multi-item receipts default to category subtotals (Priority: P2)

**Goal**: Multi-item confirmations show category subtotals by default, with an optional setting to include per-item details.

**Independent Test**: Multi-item confirmation shows subtotal lines with no per-item lines by default; enabling preference shows per-item lines.

### Tests for User Story 3

- [ ] T017 [P] [US3] Add unit tests for subtotal grouping logic in `tests/test_reply_composer.py`
- [ ] T018 [P] [US3] Add tests for preference toggle (default off vs on) in `tests/test_message_handler_reply.py`

### Implementation for User Story 3

- [ ] T019 [US3] Implement category subtotal computation and rendering in `services/reply_composer.py`
- [ ] T020 [US3] Add per-item detail rendering (compact) controlled by `confirmation_show_item_details` preference in `services/reply_composer.py`
- [ ] T021 [US3] Add bot-side preference resolution (tenant-scoped) with safe defaults in `services/tenant_settings.py` (or `services/confirmation_display_settings.py`)
- [ ] T022 [US3] Extend the web settings API/UI to allow toggling the preference in `web/src/` settings area (and persist via existing settings storage)

**Checkpoint**: US3 complete — subtotals default, per-item details gated by setting, tests cover both

---

## Phase 6: User Story 4 - How-to / help questions return concise guidance (Priority: P2)

**Goal**: Help/how-to questions about editing return short guidance instead of being rejected as unsupported.

**Independent Test**: Send “how do I delete?” and get a concise help response; unrelated chat still returns unsupported.

### Tests for User Story 4

- [ ] T023 [P] [US4] Add tests for help intent detection and response in `tests/test_message_handler_reply.py`
- [ ] T024 [P] [US4] Add localization tests for help responses in `tests/` (ja/en/zh baseline)

### Implementation for User Story 4

- [ ] T025 [US4] Implement help intent detection and routing in `services/intent.py` or `services/message_handler.py`
- [ ] T026 [US4] Add concise help message templates (ja/en/zh) per `specs/017-simplify-expense-reply/contracts/help-intent.md` in `services/confirmation_i18n.py` (or a new i18n module)
- [ ] T027 [US4] Ensure unsupported/non-expense messages remain rejected when not help-related in `services/message_handler.py`

**Checkpoint**: US4 complete — how-to questions get short help, other non-expense stays unsupported

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Consistency, docs, and validation against quickstart

- [ ] T028 [P] Align reply-edit summaries to the same sectioned composer style (where appropriate) in `services/reply_summary.py`
- [ ] T029 Update documentation examples in `specs/017-simplify-expense-reply/contracts/*.md` to match final behavior
- [ ] T030 Run the end-to-end quickstart steps and update `specs/017-simplify-expense-reply/quickstart.md` with any discovered gotchas
- [ ] T031 Run full bot test suite and fix regressions in `tests/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — blocks all user stories
- **User Stories (Phase 3+)**: Depend on Foundational
- **Polish (Phase 7)**: Depends on completing the desired user stories

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependency on other stories
- **US2 (P1)**: Can start after Foundational; touches reply-edit flows and should be validated independently
- **US3 (P2)**: Can start after Foundational; depends on composer and preference resolution
- **US4 (P2)**: Can start after Foundational; depends on intent routing conventions

### Parallel Opportunities

- [P] tasks in Phase 1–2 can run in parallel if assigned to different owners (tests/docs vs composer vs settings scaffolding)
- After Foundation, US1 and US4 can be developed in parallel (confirmation formatting vs help routing)
- US3 web/UI work can proceed in parallel with bot subtotal rendering once the preference interface is defined

---

## Implementation Strategy

### MVP First (US1)

1. Phase 1 → Phase 2
2. Phase 3 (US1) with tests
3. Validate: confirmation replies are compact for single-item and do not include the instruction block

### Incremental Delivery

1. Add US2 (YES confirm) and validate reply-edit safety
2. Add US3 (subtotals + setting) and validate multi-item receipts
3. Add US4 (help intent) to restore discoverability without clutter
