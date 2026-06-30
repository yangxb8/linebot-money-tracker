# Tasks: Budget Pace Alert in LINE Bot Replies

**Input**: Design documents from `/specs/015-budget-pace-alert/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; **012-monthly-budget-manager** (`get_budget_summary` RPC) and **005-expense-reply-edits** on branch baseline

**Organization**: Tasks grouped by user story. **MVP = User Story 1** (pace warning on new expense log).

**Tests**: Included per constitution Test-First Delivery and plan.md testing strategy.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to spec user stories (US1–US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold modules and verify dependencies before core pace logic

- [ ] T001 Verify `get_budget_summary` RPC is available in Supabase per `specs/015-budget-pace-alert/quickstart.md` prerequisites (no migration required for this feature)
- [ ] T002 [P] Add dataclasses `BudgetLevelCandidate`, `PaceEvaluation`, `PaceWarning`, and `HealthResult` in `services/budget_pace.py` per `specs/015-budget-pace-alert/data-model.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core pace evaluation, RPC fetch, i18n templates, and prepend helper — MUST complete before user story phases

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Implement `compute_budget_health()` in `services/budget_pace.py` mirroring `web/src/lib/budget/health.ts` (`pace_ratio > 1` = ahead)
- [ ] T004 [P] Implement `fetch_budget_summary()` Supabase RPC wrapper in `services/budget_pace.py` per `specs/015-budget-pace-alert/contracts/budget-pace-evaluation.md`
- [ ] T005 Implement `build_level_candidates()` in `services/budget_pace.py` (L2 → L1 → total; skip undefined limits; FR-003)
- [ ] T006 Implement `find_lowest_ahead_warning()` and `evaluate_pace_warnings()` in `services/budget_pace.py` (lowest-ahead rule per spec clarification)
- [ ] T007 [P] Add `fetch_category_display_names()` helper querying `category_nodes` in `services/budget_pace.py`
- [ ] T008 [P] Create `services/budget_pace_i18n.py` with ja/en/zh template strings per `specs/015-budget-pace-alert/contracts/budget-pace-reply.md`
- [ ] T009 Implement `format_pace_warnings()` and `maybe_prepend_budget_pace_warning()` (template-only path) in `services/budget_pace.py` with FR-013 try/except returning body unchanged on failure
- [ ] T010 [P] Add unit tests for `compute_budget_health()` in `tests/test_budget_pace.py` using vectors from `web/src/lib/budget/health.test.ts`
- [ ] T011 [P] Add unit tests for lowest-ahead selection (L2 vs L1 vs total) and skipped undefined levels in `tests/test_budget_pace.py`

**Checkpoint**: Pace evaluation callable with mocked RPC; template prepend works in isolation

---

## Phase 3: User Story 1 - Overspend Reminder on New Expense Log (Priority: P1) 🎯 MVP

**Goal**: After logging an expense, prepend pace warning at lowest ahead-of-pace cascade level before confirmation reply

**Independent Test**: Set L2 外食 ¥30k budget, pre-spend ¥25k by day 10, log ¥3k 外食 → reply starts with emoji warning (~¥250/day) then standard confirmation; on-pace or no-budget → no warning

### Tests for User Story 1

- [ ] T012 [P] [US1] Add unit tests for `maybe_prepend_budget_pace_warning()` ahead-of-pace, on-pace, and no-budget cases in `tests/test_budget_pace.py`
- [ ] T013 [P] [US1] Add handler tests for pace prepend on successful text log in `tests/test_message_handler_persistence.py`

### Implementation for User Story 1

- [ ] T014 [US1] Wire `maybe_prepend_budget_pace_warning()` into `services/message_handler.py` after `insert_expenses` in `_enrich_and_persist_items` (text path)
- [ ] T015 [US1] Wire pace prepend into image/receipt expense path in `services/message_handler.py`
- [ ] T016 [US1] Support multi-item distinct path warnings (dedupe by category path; combine blocks) in `services/budget_pace.py` per FR-012
- [ ] T017 [US1] Pass correct `TenantContext` (personal vs group) into pace evaluation from `services/message_handler.py` per FR-010/FR-011

**Checkpoint**: New expense logs prepend pace warning when applicable; group ledger uses group budgets

---

## Phase 4: User Story 2 - Overspend Reminder on Reply-Edit (Priority: P1)

**Goal**: Category or amount reply-edits re-evaluate pace and prepend warning on edit-summary reply when lowest level is ahead

**Independent Test**: Log on-pace unbudgeted expense → reply-edit category to ahead-of-pace budgeted category → edit reply begins with pace warning; delete/restore → no warning

### Tests for User Story 2

- [ ] T018 [P] [US2] Add reply-edit tests for category and amount pace prepend in `tests/test_reply_edit.py`

### Implementation for User Story 2

- [ ] T019 [US2] Wire pace prepend after successful category `update` in `services/reply_edit.py` `apply_edit_intent`
- [ ] T020 [US2] Wire pace prepend after successful amount `update` in `services/reply_edit.py` `apply_edit_intent`
- [ ] T021 [US2] Skip pace evaluation for delete, restore, clarify, and non-budget field-only edits in `services/reply_edit.py`

**Checkpoint**: Reply-edit category/amount changes trigger same pace logic as new logs

---

## Phase 5: User Story 3 - Localized Reminder Tone with Emoji (Priority: P2)

**Goal**: Conversational LLM-generated warnings with emoji and template fallback; ja/en/zh; blank-line separation from confirmation

**Independent Test**: Ahead-of-pace log in ja/en/zh → warning is conversational, starts with emoji, names category, states daily ¥; LLM failure → template fallback; blank line before confirmation

### Tests for User Story 3

- [ ] T022 [P] [US3] Add unit tests for LLM path and template fallback on Gemini failure in `tests/test_budget_pace.py`

### Implementation for User Story 3

- [ ] T023 [P] [US3] Create `services/budget_pace_prompt.py` with structured LLM prompt builder per `specs/015-budget-pace-alert/contracts/budget-pace-reply.md`
- [ ] T024 [US3] Integrate `gemini.generate_reply()` into `maybe_prepend_budget_pace_warning()` under `llm_operation_scope('budget_pace')` in `services/budget_pace.py`
- [ ] T025 [P] [US3] Register `budget_pace` operation type in `services/metered_gemini.py` if not already covered by existing metering scopes
- [ ] T026 [US3] Enforce `"{warning}\n\n{body}"` blank-line separation in `services/budget_pace.py` per SC-004

**Checkpoint**: Warnings use LLM when available; templates cover all three languages; visual separation from confirmation body

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, regression fixes, and quickstart validation

- [ ] T027 [P] Update `tests/test_message_handler_persistence.py` — replace or split `test_no_budget_impact_text` to allow pace text only when ahead of pace
- [ ] T029 [P] Add FR-013 isolation tests (RPC error, Supabase unconfigured → body unchanged) in `tests/test_budget_pace.py`
- [ ] T028 Run `specs/015-budget-pace-alert/quickstart.md` manual validation and document any gaps in task notes or fix code
- [ ] T030 Run `python3 -m pytest -q` for `tests/test_budget_pace.py`, `tests/test_message_handler_persistence.py`, and `tests/test_reply_edit.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T002 — **BLOCKS all user stories**
- **User Story 1 (Phase 3)**: Depends on Foundational — **MVP**
- **User Story 2 (Phase 4)**: Depends on Foundational; reuses `maybe_prepend_budget_pace_warning()` from Phase 2/3
- **User Story 3 (Phase 5)**: Depends on T009 (template prepend); can parallel with US2 after Foundational
- **Polish (Phase 6)**: Depends on desired user stories complete

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational — no dependency on US2/US3
- **US2 (P1)**: Independent after Foundational — shares prepend helper with US1 but testable via reply-edit only
- **US3 (P2)**: Enhances formatting for US1/US2; template path already works without US3

### Within Each User Story

- Tests (T010–T013, T018, T025) written to fail before implementation tasks in same phase
- Core `budget_pace.py` logic before `message_handler` / `reply_edit` hooks
- LLM integration (US3) after template prepend works (T009)

### Parallel Opportunities

- **Phase 1**: T002 parallel with T001
- **Phase 2**: T003, T004, T007, T008, T010, T011 in parallel after T002; then T005 → T006 → T009 sequentially
- **Phase 3**: T012, T013 parallel; T014, T015 can parallel after T009
- **Phase 4**: T018 parallel with T019–T021 prep
- **Phase 5**: T022, T024, T025 parallel; T023 after T022
- **Phase 6**: T027, T029 parallel

---

## Parallel Example: User Story 1

```bash
# Tests first (parallel):
T012: unit tests for maybe_prepend in tests/test_budget_pace.py
T013: handler integration tests in tests/test_message_handler_persistence.py

# Implementation (after T009):
T014: text path hook in services/message_handler.py
T015: image path hook in services/message_handler.py
```

---

## Parallel Example: Foundational

```bash
# Parallel core modules:
T003: compute_budget_health in services/budget_pace.py
T004: fetch_budget_summary in services/budget_pace.py
T008: budget_pace_i18n.py templates

# Then sequential:
T005 → T006 → T009
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T011) — **CRITICAL**
3. Complete Phase 3: User Story 1 (T012–T017)
4. **STOP and VALIDATE**: `python3 local_run.py --text "..."` with budget configured; confirm prepend behavior
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → pace engine ready
2. US1 → new expense warnings (MVP)
3. US2 → reply-edit warnings
4. US3 → LLM conversational tone + metering
5. Polish → regression suite green

### Parallel Team Strategy

1. Team completes Foundational together
2. Then:
   - Developer A: US1 (`message_handler.py`)
   - Developer B: US2 (`reply_edit.py`)
   - Developer C: US3 (LLM + i18n polish)
3. Merge and run Polish phase

---

## Notes

- No new Supabase migrations — read-only RPC use
- Fiscal month from expense date via RPC (not hardcoded calendar)
- Lowest-ahead rule: evaluate L2, L1, total; warn at first `pace_ratio > 1` in that order
- FR-013: never block confirmation — log and skip warning on any failure
- Commit after each task or logical group; stop at any checkpoint to validate story independently
