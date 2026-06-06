# Tasks: Supabase Expense Storage & Budget Analysis

**Input**: Design documents from `/specs/004-supabase-expense-storage/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks grouped by user story. **MVP = User Story 1 + User Story 2** (both P1 — persist with categorization and confirmation reply).

**Tests**: Included per constitution Test-First Delivery and plan.md testing strategy.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to spec user stories (US1–US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and environment for Supabase persistence

- [X] T001 Add `supabase` package to `requirements.txt`
- [X] T002 [P] Extend `.env.example` with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and optional `LOCAL_LINE_USER_ID` per `specs/004-supabase-expense-storage/contracts/environment-variables.md`
- [X] T003 [P] Create `services/message_context.py` with `MessageContext` dataclass (`line_user_id`, `source_message_id`)
- [X] T004 [P] Create `services/supabase_client.py` with lazy Supabase client factory reading env vars

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema, taxonomy seed, and shared services — MUST complete before user story phases

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Create `data/category_taxonomy_ja.yaml` with Japanese-household L1–L3 category tree including `unknown` node per `specs/004-supabase-expense-storage/data-model.md`
- [X] T006 Create `supabase/migrations/20260606120000_expense_schema.sql` with `category_nodes`, `expenses`, `monthly_budgets`, RLS, taxonomy seed, unique idempotency constraint, and RPC functions `monthly_expense_total` / `yearly_expense_total` per `specs/004-supabase-expense-storage/contracts/supabase-schema.md`
- [X] T007 Apply migration to `https://nyuenufldaqsjybjhawl.supabase.co` via Supabase MCP `apply_migration` (server `project-0-linebot-money-tracker-supabase`) or Dashboard SQL editor; verify with `list_tables`
- [X] T008 [P] Implement `services/category_taxonomy.py` with `load_category_taxonomy()`, `resolve_code()`, and denormalized L1/L2/L3 ID computation per `specs/004-supabase-expense-storage/data-model.md`
- [X] T009 [P] Add `extract_line_user_id()` and `extract_source_message_id()` to `services/line_event.py`
- [X] T010 [P] Add unit tests for taxonomy code resolution and denormalized ancestor columns in `tests/test_category_taxonomy.py`

**Checkpoint**: Blank Supabase project has expense schema; taxonomy loadable in Python

---

## Phase 3: User Story 1 - Persist Detected Expenses (Priority: P1) 🎯 MVP (part 1)

**Goal**: After expense detection, insert rows into Supabase via predefined repository methods; idempotent on message ID; storage failure does not block reply

**Independent Test**: Log expense via console with Supabase configured → row in `expenses` with amount, currency, description, `line_user_id`, `source_message_id`; rerun same message ID → no duplicates; unset Supabase env → reply still returned

### Tests for User Story 1

- [X] T011 [P] [US1] Add unit tests for `insert_expenses` idempotency, conflict skip, and non-raising error path in `tests/test_expense_repository.py` (mock Supabase client — no dynamic SQL)
- [X] T012 [P] [US1] Add handler tests for persist-on-success and skip-on-storage-error in `tests/test_message_handler_persistence.py`

### Implementation for User Story 1

- [X] T013 [US1] Implement `services/expense_repository.py` with `ExpenseInsertRow`, `PersistResult`, and `insert_expenses()` using fixed `.table('expenses').insert()` only per `specs/004-supabase-expense-storage/contracts/expense-persistence.md` and `contracts/llm-db-boundary.md`
- [X] T014 [US1] Add `build_insert_row()` helper in `services/expense_repository.py` to compute `assigned_level` and `category_l1/l2/l3_id` from resolved category node
- [X] T015 [US1] Extend `process_text_message()` and `process_image_message()` in `services/message_handler.py` to accept optional `MessageContext` and call `insert_expenses()` after detection (category may be `unknown` until US2 enriches flow)
- [X] T016 [US1] Pass `MessageContext` from `main.py` `handle_callback` using `extract_line_user_id` / `extract_source_message_id` in `main.py`
- [X] T017 [US1] Pass synthetic `MessageContext` (`LOCAL_LINE_USER_ID`, fresh `uuid4()`) from `local_run.py`
- [X] T018 [US1] Skip persistence with WARNING when `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` missing (console mode) in `services/expense_repository.py`
- [X] T019 [US1] Update existing tests in `tests/test_message_handler.py` for optional `MessageContext` parameter

**Checkpoint**: Expenses persist to Supabase; idempotent retries; reply unchanged on DB failure

---

## Phase 4: User Story 2 - Auto-Categorize with Japanese Taxonomy (Priority: P1) 🎯 MVP (part 2)

**Goal**: LLM returns category JSON only; app validates, maps codes, persists guess, reply shows guess + up to 3 alternatives + confirm prompt (no DB update on user correction)

**Independent Test**: Log supermarket / train / utility expenses → stored category codes match taxonomy; reply shows `Category (guess): …` and numbered alternatives; invalid LLM code → `unknown`

### Tests for User Story 2

- [X] T020 [P] [US2] Add unit tests for categorize JSON parsing, schema validation, and `unknown` fallback in `tests/test_categorize.py`
- [X] T021 [P] [US2] Add handler tests for enriched reply format (no budget impact lines) in `tests/test_message_handler_persistence.py`

### Implementation for User Story 2

- [X] T022 [US2] Implement `services/categorize.py` with Gemini prompt returning `{guessed_category_code, alternatives[]}` JSON only per `specs/004-supabase-expense-storage/contracts/categorization-reply.md`
- [X] T023 [US2] Add jsonschema validation for categorize response in `services/categorize.py`
- [X] T024 [US2] Integrate categorize → resolve codes → `build_insert_row()` in expense pipeline inside `services/message_handler.py`
- [X] T025 [US2] Extend `format_expense_items()` in `services/message_handler.py` with category path, confirmation prompt, and up to 3 numbered alternatives per `contracts/categorization-reply.md`
- [X] T026 [US2] Verify FR-010: expense replies never include budget impact text in `services/message_handler.py`

**Checkpoint**: Full persist + categorize + confirmation reply flow works end-to-end

---

## Phase 5: User Story 3 - Analysis-Ready Schema & Rollup Queries (Priority: P2)

**Goal**: Predefined RPC functions return correct monthly/yearly totals with JST boundaries and FR-004/FR-005 rollup rules

**Independent Test**: Seed expenses across months/years and category levels; call `monthly_expense_total` / `yearly_expense_total` via repository; verify acceptance scenarios in spec User Story 3

### Tests for User Story 3

- [X] T027 [P] [US3] Add rollup tests for L1-only vs L3 assignments and JST month filtering in `tests/test_expense_rollup.py` (mock RPC or integration marker)

### Implementation for User Story 3

- [X] T028 [US3] Implement `monthly_expense_total()` and `yearly_expense_total()` RPC wrappers in `services/expense_repository.py` with fixed RPC names only
- [X] T029 [US3] Add SQL verification examples for rollup scenarios to `specs/004-supabase-expense-storage/quickstart.md`
- [X] T030 [US3] Confirm `monthly_budgets` table exists as empty placeholder (no bot CRUD) after migration

**Checkpoint**: Analysis queries validated; budget table ready for follow-on spec

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness, docs, and regression safety

- [X] T031 [P] Add optional Supabase env validation to webhook startup in `main.py` when persistence is required for deployment
- [X] T032 [P] Update root `README.md` with Supabase persistence section linking to `specs/004-supabase-expense-storage/quickstart.md`
- [X] T033 Run full test suite `pytest -q` and fix regressions
- [X] T034 [P] Manual validation of `specs/004-supabase-expense-storage/quickstart.md` against live project `nyuenufldaqsjybjhawl`
- [X] T035 Mark completed tasks `[X]` in this file after implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2
- **US2 (Phase 4)**: Depends on Phase 3 (insert path must exist before categorize integration)
- **US3 (Phase 5)**: Depends on Phase 2 migration RPCs; testable after US1/US2 seed data exists
- **Polish (Phase 6)**: Depends on desired story completion

### User Story Dependencies

| Story | Depends on | Notes |
| ----- | ---------- | ----- |
| US1 | Foundational | Core insert + idempotency |
| US2 | US1 | Categorization enriches insert rows and reply |
| US3 | Foundational (+ US1/US2 for realistic test data) | RPC/query validation only |

### Parallel Opportunities

**Phase 1** (after T001): T002, T003, T004 in parallel

**Phase 2** (after T006): T008, T009, T010 in parallel; T005 parallel with T006 prep

**Phase 3**: T011, T012 in parallel before T013

**Phase 4**: T020, T021 in parallel before T022

**Phase 5**: T027 parallel with T028 prep

**Phase 6**: T031, T032, T034 in parallel

---

## Parallel Example: Foundational Phase

```bash
# After T006 migration file exists:
Task T008: services/category_taxonomy.py
Task T009: services/line_event.py
Task T010: tests/test_category_taxonomy.py
```

## Parallel Example: User Story 1

```bash
Task T011: tests/test_expense_repository.py
Task T012: tests/test_message_handler_persistence.py
# Then sequentially: T013 → T014–T019
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**apply migration to blank Supabase project**)
3. Complete Phase 3: US1 — persist with `unknown` category acceptable mid-flight
4. Complete Phase 4: US2 — full categorize + confirmation reply
5. **STOP and VALIDATE**: `python local_run.py --text "スーパー 3500円"` → reply + row in `expenses`
6. Phase 5 (US3) can follow for analysis query confidence

### Incremental Delivery

1. Setup + Foundational → schema live on Supabase
2. US1 → expenses persist (even with `unknown` category)
3. US2 → categorization + rich reply
4. US3 → rollup RPC verification
5. Polish → production env + docs

### LLM / DB Boundary (all phases)

- Gemini outputs **JSON only** (expenses + category codes)
- App validates and calls **`insert_expenses()`** and fixed **RPC names** only
- See `specs/004-supabase-expense-storage/contracts/llm-db-boundary.md`

---

## Notes

- Supabase MCP server name: `project-0-linebot-money-tracker-supabase`
- Target project URL: `https://nyuenufldaqsjybjhawl.supabase.co` (verified blank)
- Deferred to follow-on spec: user category correction persistence, budget CRUD, budget impact in reply, analysis bot commands
- Avoid LLM-generated SQL anywhere in the codebase
