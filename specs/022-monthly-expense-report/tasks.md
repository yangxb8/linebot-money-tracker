---
description: "Task list for Monthly Expense Report feature implementation"
---

# Tasks: Monthly Expense Report

**Input**: Design documents from `/specs/022-monthly-expense-report/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; features **012/015/016/019** baseline (budgets, pace, persona, reply language)

**Tests**: Included per constitution Test-First Delivery, AGENTS.md suite expansion, and plan.md — pytest unit + `tests/functional/bot/` for primary acceptance scenarios. No new web/Playwright tasks in v1 (LINE-only surface). Manual quickstart checklist in Polish.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Bot: `services/`, `tests/`, `local_run.py`, `main.py` at repository root
- Schema/Storage: `supabase/migrations/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module scaffolding and i18n placeholders for monthly report

- [X] T001 Create empty bot module stubs `services/monthly_report.py`, `services/monthly_report_period.py`, `services/monthly_report_snapshot.py`, `services/monthly_report_insights.py`, `services/monthly_report_render.py`, `services/monthly_report_repository.py` with module docstrings referencing `specs/022-monthly-expense-report/contracts/`
- [X] T002 [P] Add monthly-report i18n key placeholders in `services/confirmation_i18n.py` (`monthly_report_tip`, `monthly_report_preparing`, `monthly_report_in_progress`, `monthly_report_failed`, `monthly_report_caption`, `monthly_report_future`, empty/no-budget helpers — ja/en/zh)
- [X] T003 [P] Add matching persona-flavored keys in `services/persona_i18n.py` for the same monthly-report message keys

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, Storage, shared period/repo helpers, and BotReply image payload that MUST complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create Supabase migration `supabase/migrations/YYYYMMDDHHMMSS_monthly_report_artifacts.sql` per `specs/022-monthly-expense-report/contracts/supabase-schema-delta.md` and `data-model.md` (`monthly_report_artifacts`, `monthly_report_tips`, indexes, RLS lockdown, private bucket `monthly-reports`)
- [X] T005 Apply migration to Supabase project `https://nyuenufldaqsjybjhawl.supabase.co` and verify tables + private bucket `monthly-reports` (note result in `specs/022-monthly-expense-report/quickstart.md` if needed)
- [X] T006 [P] Implement fiscal period helpers in `services/monthly_report_period.py` (reuse `fiscal_period_start_for_date` / `_fetch_fiscal_start_day` from `services/budget_pace.py`; previous completed / current / named period resolution; reject future)
- [X] T007 [P] Implement repository helpers in `services/monthly_report_repository.py` (artifact upsert/load by tenant+period_start; tip insert/exists; Storage upload; signed URL generation; fingerprint fields)
- [X] T008 Extend `BotReply` in `services/message_context.py` with optional image payload (`original_url`, `preview_url`, optional local path/bytes for harness) per `contracts/monthly-report-bot.md`
- [X] T009 Update `main.py` `_reply_and_save_confirmation` (and related reply helpers) to send `TextMessage` and/or LINE `ImageMessage` when `BotReply.image` is set
- [X] T010 [P] Update `local_run.py` to write/print report PNG path (and caption) when `BotReply.image` is present
- [X] T011 [P] Add unit tests for period resolution in `tests/test_monthly_report_period.py` (start day 1 vs non-1; previous vs current; future rejected)

**Checkpoint**: Foundation ready — migration applied, period/repo helpers + BotReply image path in place

---

## Phase 3: User Story 1 - Ask for a monthly report and receive one summary image (Priority: P1) 🎯 MVP

**Goal**: User can ask via dedicated `monthly_report` intent and receive one summary image for the ledger’s default/named period (default = previous completed fiscal period)

**Independent Test**: With expenses+budgets in the previous period, send “monthly report” / “レポート” and get one image (or harness PNG) for that ledger; expense/wish intents unchanged

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [P] [US1] Add intent classification tests for `monthly_report` (phrase gate + LLM parse stub) in `tests/test_monthly_report_intent.py`
- [X] T013 [P] [US1] Add functional bot journey skeleton in `tests/functional/bot/test_monthly_report_journey.py` asserting report ask does not insert expenses/wish items and returns image or caption path when artifact ready (mocked repo/Gemini/LINE)

### Implementation for User Story 1

- [X] T014 [US1] Extend `TextMessageIntent` and `COMBINED_TEXT_INTENT_PROMPT` in `services/intent.py` with `monthly_report` (+ prefer-over rules) per `contracts/monthly-report-bot.md`
- [X] T015 [P] [US1] Add deterministic phrase gate for report asks (JP/EN) in `services/intent.py` or a small `services/monthly_report_intent.py`
- [X] T016 [US1] Implement minimal sync prepare→render path in `services/monthly_report_render.py` + `services/monthly_report.py` that produces a PNG (placeholder chart acceptable for MVP wiring) and stores via repository
- [X] T017 [US1] Wire `monthly_report` branch in `services/message_handler.py` to resolve period (default previous completed), load/create ready artifact, and return `BotReply` with image + caption i18n
- [X] T018 [US1] Handle invalid/future period and missing-ledger errors with i18n text-only replies in `services/monthly_report.py` / `message_handler.py`
- [X] T019 [US1] Expand `tests/functional/bot/test_monthly_report_journey.py` for personal vs group ledger period default and “no expense side effects”

**Checkpoint**: User Story 1 complete — dedicated ask returns one image for previous completed period

---

## Phase 4: User Story 2 - Lazy first request with same-turn delivery when ready soon (Priority: P1)

**Goal**: First ask starts lazy prepare; same-turn image if ready within ~8s; otherwise preparing/ask-again; later ask delivers; in-progress and refresh-on-fingerprint-change work

**Independent Test**: Force slow prepare → first ask gets preparing text; mark ready → second ask gets image; in-progress ask gets wait copy; change expenses → next ask refreshes

### Tests for User Story 2

- [X] T020 [P] [US2] Add unit tests in `tests/test_monthly_report_request.py` for same-turn ready vs ask-again timeout, in-progress reply, failed retry, fingerprint stale→refresh
- [X] T021 [P] [US2] Extend `tests/functional/bot/test_monthly_report_journey.py` with preparing → ask-again → deliver journey (mocked clocks/artifact states)

### Implementation for User Story 2

- [X] T022 [US2] Implement artifact state machine + fingerprint compute/compare in `services/monthly_report_repository.py` / `services/monthly_report.py` (`preparing`/`ready`/`failed`, data+style fingerprints)
- [X] T023 [US2] Implement same-turn wait budget (~8s) and background continuation (`asyncio.create_task` or equivalent) in `services/monthly_report.py` without reusing expired LINE reply tokens
- [X] T024 [US2] Return `monthly_report_preparing` / `monthly_report_in_progress` / `monthly_report_failed` i18n replies from `services/monthly_report.py` for non-ready paths
- [X] T025 [US2] On ask when ready+fingerprint match, resend existing artifact without full re-prepare; on mismatch, re-enter preparing/refresh path

**Checkpoint**: User Story 2 complete — lazy prepare, same-turn/ask-again, refresh semantics work

---

## Phase 5: User Story 3 - Budget-aware insights on the report image (Priority: P1)

**Goal**: Primary graph is budget vs actual (total + ≤3 worst-variance categories); commentary grounded in budget performance; no-budget fallback spending summary

**Independent Test**: Over-budget period with multiple category budgets → image/snapshot includes total + worst-variance cats; no-budget ledger → spending fallback + clear “no budget” copy

### Tests for User Story 3

- [X] T026 [P] [US3] Add unit tests in `tests/test_monthly_report_snapshot.py` for total inclusion, worst-variance ranking (≤3), no-budget fallback, pace fields aligned with `budget_pace` health
- [X] T027 [P] [US3] Add render/snapshot assertion helpers or tests in `tests/test_monthly_report_render.py` that ready artifacts’ `snapshot_json` drives budget-vs-actual primary series (not category-share-only when budgeted)
- [X] T028 [P] [US3] Extend `tests/functional/bot/test_monthly_report_journey.py` for budgeted vs no-budget commentary/graph expectations (mocked snapshot/render)

### Implementation for User Story 3

- [X] T029 [US3] Implement `services/monthly_report_snapshot.py` using `get_budget_summary` / `budget_pace` helpers to build Budget Comparison Snapshot per `data-model.md` and `contracts/monthly-report-artifact.md`
- [X] T030 [P] [US3] Implement insight copy in `services/monthly_report_insights.py` (Gemini metered + template fallback via i18n/persona) focused on meeting budget
- [X] T031 [US3] Upgrade `services/monthly_report_render.py` so primary visual is budget vs actual (total + selected categories) with commentary block; spending-summary fallback when no budgets
- [X] T032 [US3] Persist `snapshot_json` + `insight_text` on ready artifacts in `services/monthly_report_repository.py` and use them for delivery captions

**Checkpoint**: User Story 3 complete — budget-first chart + insights; safe no-budget fallback

---

## Phase 6: User Story 4 - New-period tip that previous report is available on ask (Priority: P2)

**Goal**: First message of a new fiscal period in a conversation gets a text-only tip once; groups tip once per conversation; tip does not start prepare; report ask takes precedence

**Independent Test**: After rollover, first message tips; second message / other group member does not; tip has no image; monthly-report as first message does not require a useless tip-only turn

### Tests for User Story 4

- [X] T033 [P] [US4] Add unit tests in `tests/test_monthly_report_tip.py` for once-per-conversation tip persistence and skip-when-already-shown
- [X] T034 [P] [US4] Extend `tests/functional/bot/test_monthly_report_journey.py` for tip on first message, no repeat in group, and report-ask precedence

### Implementation for User Story 4

- [X] T035 [US4] Implement `maybe_new_period_tip` in `services/monthly_report.py` using `monthly_report_tips` via `services/monthly_report_repository.py`
- [X] T036 [US4] Integrate tip prepend/append into `services/message_handler.py` primary reply path without starting artifact prepare
- [X] T037 [US4] Ensure `monthly_report` first-message path omits or folds tip per FR-016 in `services/monthly_report.py` / `message_handler.py`

**Checkpoint**: User Story 4 complete — text-only once-per-conversation tip

---

## Phase 7: User Story 5 - Consistent visual style reflecting persona, overspend, and top-spend theme (Priority: P2)

**Goal**: Shared layout family; commentary follows persona/language/emoji; stronger caution when overspent/ahead; accent from highest-spend category

**Independent Test**: Two personas/languages produce matching layout with different voice; over-budget vs healthy differ in caution cues; Food vs Transport top-spend changes accent

### Tests for User Story 5

- [X] T038 [P] [US5] Add unit tests in `tests/test_monthly_report_render.py` for style fingerprint inputs (persona/language/emoji), overspend severity styling flags, and top-spend theme selection tie-break
- [X] T039 [P] [US5] Extend functional coverage in `tests/functional/bot/test_monthly_report_journey.py` asserting style_fingerprint refresh when persona/language settings change

### Implementation for User Story 5

- [X] T040 [US5] Pass resolved persona, reply language, and emoji level into insights/render from `services/monthly_report.py` (reuse `resolve_persona_for_tenant` / reply-language helpers)
- [X] T041 [P] [US5] Apply overspend severity visual/copy cues and top-spend category accent in `services/monthly_report_render.py` while keeping shared layout frame
- [X] T042 [US5] Include style inputs in `style_fingerprint` so setting changes force refresh in `services/monthly_report.py`

**Checkpoint**: User Story 5 complete — consistent layout with persona/overspend/theme adaptation

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Docs, architecture sync, suite green, quickstart validation

- [X] T043 [P] Update `docs/ARCHITECTURE.md` for monthly-report intent, artifact/tip tables, Storage bucket, and LINE image reply path (required before merge per architecture-docs gate)
- [X] T044 [P] Align `specs/022-monthly-expense-report/quickstart.md` with final harness commands and any migration filename
- [X] T045 Run `python3 -m pytest -q` (including `tests/functional/bot/`) and fix regressions from intent/BotReply/main changes
- [X] T046 Manually walk `specs/022-monthly-expense-report/quickstart.md` acceptance checklist and capture evidence under `/opt/cursor/artifacts/` when implementing in Cloud Agent
- [X] T047 [P] Add brief logging for prepare start/ready/fail, tip shown, and delivery in `services/monthly_report.py` / repository

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP
- **US2 (Phase 4)**: Depends on US1 deliver path existing (extends prepare orchestration)
- **US3 (Phase 5)**: Depends on US1 render/store path; can overlap late US2 but needs artifact PNG pipeline
- **US4 (Phase 6)**: Depends on Foundational tip table + period helpers; independent of image quality (US3/US5)
- **US5 (Phase 7)**: Depends on US3 render/insights pipeline
- **Polish (Phase 8)**: Depends on desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — MVP image ask/deliver
- **US2 (P1)**: After US1 — lazy/same-turn/ask-again
- **US3 (P1)**: After US1 (ideally after or with US2) — budget-first snapshot/insights/render
- **US4 (P2)**: After Foundational — can parallel US2/US3 once tip schema exists
- **US5 (P2)**: After US3 — styling polish on real chart/insights

### Within Each User Story

- Tests FIRST (fail) before implementation
- Repository/period before orchestration
- Orchestration before handler wiring
- Story complete before next priority when sequential

### Parallel Opportunities

- T002/T003 in Setup
- T006/T007/T011 in Foundational (after T004 designed; T005 sequential apply)
- US1 tests T012/T013 parallel; US1 gate T015 parallel with early T016 after intent types exist
- US2 tests T020/T021; US3 tests T026/T027/T028; US4 tests T033/T034; US5 tests T038/T039
- US4 implementation can proceed in parallel with US2/US3 after Foundational
- Polish T043/T044/T047 parallel

---

## Parallel Example: User Story 1

```bash
# Tests first:
Task: "Add intent classification tests in tests/test_monthly_report_intent.py"
Task: "Add functional bot journey skeleton in tests/functional/bot/test_monthly_report_journey.py"

# Then implementation (intent + gate can parallel early):
Task: "Extend TextMessageIntent in services/intent.py"
Task: "Add phrase gate in services/intent.py or services/monthly_report_intent.py"
```

---

## Parallel Example: User Story 3

```bash
Task: "Unit tests in tests/test_monthly_report_snapshot.py"
Task: "Render/snapshot tests in tests/test_monthly_report_render.py"
Task: "Functional budgeted vs no-budget cases in tests/functional/bot/test_monthly_report_journey.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Report ask returns one image for previous period
5. Demo via `local_run.py --text "monthly report"`

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → MVP image ask/deliver
3. US2 → lazy same-turn / ask-again
4. US3 → budget-vs-actual insights (core product value)
5. US4 → new-period tip
6. US5 → persona/overspend/theme polish
7. Polish → architecture doc + full suite green

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Then:
   - Dev A: US1 → US2
   - Dev B: US3 (after US1 PNG pipeline exists)
   - Dev C: US4 (after Foundational)
3. US5 after US3; Polish last

---

## Notes

- [P] tasks = different files, no incomplete-task dependencies
- [Story] labels map to US1–US5 from `spec.md`
- Exact chart library stays Pillow per research; ≤3 worst-variance categories
- Tip must never start image prepare; image never auto-pushed
- Commit after each task or logical group
- Suggested MVP scope: **US1 only** (Phases 1–3)
