---
description: "Task list for Tenant Category Memory feature implementation"
---

# Tasks: Tenant Category Memory

**Input**: Design documents from `/specs/013-tenant-category-memory/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; features **004–006**, **010** complete

**Tests**: pytest included per plan.md constitution compliance (merchant normalize/extract, memory weights, classify orchestration, reply-edit hooks). Manual quickstart checklist in Polish.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Static merchant alias data and shared constants

- [ ] T001 Create `data/merchant_aliases_ja.yaml` with 60+ Japanese merchant keys per `specs/013-tenant-category-memory/appendix-merchant-alias-seed.md`
- [ ] T002 [P] Add memory weight constants (`MEMORY_SKIP_WEIGHT_THRESHOLD`, `WEIGHT_LLM_SEED`, `WEIGHT_SILENT_CONFIRM`, `WEIGHT_USER_CORRECTION`) in `services/category_memory.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, normalization, merchant LLM extract, memory repository, and expense provenance columns that MUST complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create Supabase migration `supabase/migrations/20260628120000_category_merchant_memory.sql` per `specs/013-tenant-category-memory/contracts/supabase-schema-delta.md` (`category_merchant_memory` table, `expenses` delta columns)
- [ ] T004 Implement `get_category_accuracy_stats` RPC in `supabase/migrations/20260628120000_category_merchant_memory.sql` per `specs/013-tenant-category-memory/data-model.md`
- [ ] T005 [P] Implement YAML loader, branch stripping, generic denylist, and `normalize_merchant_key()` in `services/merchant_normalize.py`
- [ ] T006 [P] Create `tests/test_merchant_normalize.py` covering alias hits (セブン→`seven_eleven`), branch suffix strip, and generic denylist (`食費`, `買い物`)
- [ ] T007 [P] Implement `extract_merchant_name()` with JSON schema validation under `llm_operation_scope('merchant_extract')` in `services/merchant_extract.py`
- [ ] T008 [P] Create `tests/test_merchant_extract.py` with mocked Gemini responses (merchant found, null generic, invalid JSON fallback)
- [ ] T009 Implement `lookup_memory`, `upsert_llm_seed`, and `record_user_correction` in `services/category_memory.py` using Supabase service role
- [ ] T010 [P] Create `tests/test_category_memory.py` for lookup, LLM seed `+0.25`, user correction `weight=1.0`, and tenant-scoped keys
- [ ] T011 Extend `ExpenseInsertRow` and `build_insert_row()` in `services/expense_repository.py` with `category_guess_code` and `category_source` fields
- [ ] T012 Update `_row_to_dict()` and `insert_expenses()` path in `services/expense_repository.py` to persist provenance columns

**Checkpoint**: Foundation ready — migration defined, normalize/extract/memory modules testable, expenses accept provenance fields

---

## Phase 3: User Story 1 - Repeat merchant auto-categorized (Priority: P1) 🎯 MVP

**Goal**: User logs expense at a previously corrected merchant; bot assigns remembered category without category LLM; confirmation label unchanged

**Independent Test**: Correct Starbucks to `food.dining` once; log another Starbucks expense; verify `category_source=memory` and no `categorize` scope in usage logs

### Tests for User Story 1

- [ ] T013 [P] [US1] Create `tests/test_categorize_memory.py` asserting `classify_expense_with_memory` skips `classify_expense` when `weight >= 1.0`

### Implementation for User Story 1

- [ ] T014 [US1] Implement `CategoryResultWithProvenance` and `classify_expense_with_memory()` in `services/categorize.py` per `specs/013-tenant-category-memory/contracts/categorize-memory.md`
- [ ] T015 [US1] Replace `classify_expense` call with `classify_expense_with_memory` in `services/message_handler.py` `_enrich_and_persist_items()`
- [ ] T016 [US1] Pass `category_guess_code` and `category_source` from orchestrator through `build_insert_row()` in `services/message_handler.py`
- [ ] T017 [US1] Extend `tests/test_message_handler_persistence.py` to assert memory path sets `category_source='memory'` when memory repo returns `weight >= 1.0`

**Checkpoint**: User Story 1 complete — repeat merchant skips category LLM with same confirmation copy

---

## Phase 4: User Story 2 - User correction teaches tenant memory (Priority: P1)

**Goal**: Reply-edit category change upserts tenant memory so same merchant classifies correctly on next log; last writer wins within tenant

**Independent Test**: Log unknown merchant; reply-edit category to `transport.transit`; verify `category_merchant_memory` row with `weight=1.0` and `last_source=user_correction`

### Tests for User Story 2

- [ ] T018 [P] [US2] Extend `tests/test_reply_edit.py` to assert `record_user_correction` called after category `update_expense_fields`

### Implementation for User Story 2

- [ ] T019 [US2] Hook `record_user_correction()` in `services/reply_edit.py` after successful single-item category change in `apply_edit_intent()`
- [ ] T020 [US2] Hook memory update in `services/reply_edit.py` bulk category pick path (`_apply_category_bulk_pick` / category option handlers)
- [ ] T021 [US2] Pass `gemini` and expense `description` into correction hook so merchant re-extraction runs in `services/reply_edit.py`

**Checkpoint**: User Story 2 complete — explicit corrections teach per-tenant memory

---

## Phase 5: User Story 4 - Generic descriptions always use LLM (Priority: P1)

**Goal**: Vague expenses (`食費`, `買い物`) always invoke category LLM; no memory read or write for generic merchants

**Independent Test**: Log `食費 5000円` twice; verify `categorize` scope both times and no `category_merchant_memory` row for generic key

### Tests for User Story 4

- [ ] T022 [P] [US4] Add generic-path tests to `tests/test_categorize_memory.py` (null merchant → always LLM, no memory upsert)

### Implementation for User Story 4

- [ ] T023 [US4] Ensure `classify_expense_with_memory()` in `services/categorize.py` bypasses lookup and upsert when `normalize_merchant_key` returns `None`
- [ ] T024 [US4] Ensure `record_user_correction()` in `services/category_memory.py` no-ops when merchant extraction yields generic/null

**Checkpoint**: User Story 4 complete — generic descriptions never pollute memory

---

## Phase 6: User Story 6 - Group ledger shared memory (Priority: P1)

**Goal**: Group member A's correction applies to member B's future logs in same group tenant; personal memory isolated

**Independent Test**: Member A corrects `ドンキ` in group G; member B logs `ドンキホーテ` in group G; B gets A's category; personal tenant has no row

### Tests for User Story 6

- [ ] T025 [P] [US6] Add tenant isolation tests to `tests/test_category_memory.py` (`user` vs `group` same `merchant_key`, different rows)
- [ ] T026 [P] [US6] Extend `tests/test_message_handler_persistence.py` with group `TenantContext` memory hit scenario

### Implementation for User Story 6

- [ ] T027 [US6] Verify all memory queries filter by `tenant.tenant_type` and `tenant.tenant_id` in `services/category_memory.py` (no `line_user_id` scoping)
- [ ] T028 [US6] Pass group `TenantContext` through `classify_expense_with_memory` in `services/message_handler.py` (confirm existing 006 path unchanged)

**Checkpoint**: User Story 6 complete — group and personal memories are isolated per tenant

---

## Phase 7: User Story 3 - Silent confirmation strengthens memory (Priority: P2)

**Goal**: Repeat logs without category edit increase weight; second+ log can reach `weight >= 1.0` without explicit correction

**Independent Test**: Log Lawson twice without reply-edit; verify weight `0.25` then `0.75`; third log skips category LLM

### Tests for User Story 3

- [ ] T029 [P] [US3] Add silent confirm weight progression tests to `tests/test_category_memory.py` (`+0.5` when prior expense uncorrected)

### Implementation for User Story 3

- [ ] T030 [US3] Implement `find_prior_expense_for_merchant()` and `apply_silent_confirm()` in `services/category_memory.py` per research Decision 5
- [ ] T031 [US3] Call silent confirm after persist in `classify_expense_with_memory()` flow in `services/categorize.py` (compare prior expense guess vs final category, no category audit)

**Checkpoint**: User Story 3 complete — repeat logging strengthens memory without reply-edit

---

## Phase 8: User Story 5 - Backfill from historical expenses (Priority: P2)

**Goal**: One-time script seeds memory from existing expenses using YAML/heuristic merchant keys (no LLM)

**Independent Test**: Run `python scripts/backfill_category_memory.py --dry-run` then live; verify memory rows for known merchants from history

### Implementation for User Story 5

- [ ] T032 [P] [US5] Create `scripts/backfill_category_memory.py` with `--dry-run` flag and idempotent upsert per `specs/013-tenant-category-memory/research.md` Decision 8
- [ ] T033 [US5] Implement heuristic merchant extraction (YAML alias + description token) in `scripts/backfill_category_memory.py` without LLM calls
- [ ] T034 [US5] Add backfill verification queries to `specs/013-tenant-category-memory/quickstart.md` section 2 if not already sufficient

**Checkpoint**: User Story 5 complete — historical expenses seed tenant memory on deploy

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Analytics RPC validation, full regression, metering, and manual verification

- [ ] T035 [P] Add SQL smoke test or pytest for `get_category_accuracy_stats` return shape in `tests/test_category_memory.py` or `tests/web/category_accuracy_stats.test.sql`
- [ ] T036 [P] Extend `tests/test_metered_gemini.py` to cover `merchant_extract` operation scope if missing
- [ ] T037 Run full `pytest` suite from repo root and fix regressions
- [ ] T038 Execute manual checklist in `specs/013-tenant-category-memory/quickstart.md` (correction → repeat log, generic, group, analytics RPC)
- [ ] T039 Apply migration to Supabase and run `python scripts/backfill_category_memory.py` on staging; document row counts in PR notes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Stories (Phases 3–8)**: All depend on Foundational completion
- **Polish (Phase 9)**: Depends on desired user stories (minimum US1 + US2 + US4 for MVP)

### User Story Dependencies

| Story | Priority | Depends on | Notes |
| ----- | -------- | ---------- | ----- |
| US1 Repeat merchant | P1 | Foundational | MVP — memory skip path |
| US2 User correction | P1 | Foundational, US1 orchestrator | Can parallel after T014 |
| US4 Generic always LLM | P1 | Foundational | Mostly denylist; validate after US1 |
| US6 Group memory | P1 | Foundational, US1 | Tenant key scoping tests |
| US3 Silent confirm | P2 | US1, US2 | Needs prior expense + memory rows |
| US5 Backfill | P2 | Foundational normalize | Independent of live LLM path |

### Within Each User Story

- Tests before or alongside implementation (constitution test-first)
- `category_memory.py` before `categorize.py` orchestrator
- Orchestrator before `message_handler.py` wiring
- Reply-edit hooks after memory repository

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **Phase 2**: T005–T008 parallel after T003; T010 ∥ T011 after T009
- **Phase 3**: T013 ∥ T014 start; T017 after T015
- **Phases 4–6**: Test tasks marked [P] parallel within story
- **Phase 8**: T032 ∥ T033 after normalize module exists
- **Phase 9**: T035 ∥ T036 ∥ T037

---

## Parallel Example: User Story 1

```bash
# Tests + orchestrator skeleton in parallel:
Task T013: tests/test_categorize_memory.py
Task T014: services/categorize.py classify_expense_with_memory

# After T014 completes:
Task T015: services/message_handler.py wiring
Task T016: services/expense_repository.py provenance pass-through
Task T017: tests/test_message_handler_persistence.py extension
```

---

## Parallel Example: Foundational Phase

```bash
# After migration T003–T004:
Task T005: services/merchant_normalize.py
Task T006: tests/test_merchant_normalize.py
Task T007: services/merchant_extract.py
Task T008: tests/test_merchant_extract.py
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 4)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: US1 — repeat merchant skips category LLM
4. Complete Phase 4: US2 — corrections teach memory
5. Complete Phase 5: US4 — generic guardrails
6. **STOP and VALIDATE** via quickstart sections 1–2 and 5
7. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → normalize/extract/memory ready
2. US1 → repeat merchant (MVP value)
3. US2 + US4 → learning + safety
4. US6 → group ledger parity
5. US3 → silent confirm (fewer corrections needed)
6. US5 → backfill day-one accuracy
7. Polish → analytics + full regression

### Suggested MVP Scope

**Minimum shippable**: Phases 1–2 + US1 + US2 + US4 (tasks T001–T024).  
Defers silent confirm, backfill, and group-specific tests to fast follow (US3, US5, US6 polish).

---

## Notes

- Total tasks: **39**
- US1: 5 tasks | US2: 4 | US4: 3 | US6: 4 | US3: 3 | US5: 3 | Setup: 2 | Foundational: 10 | Polish: 5
- Confirmation label stays `カテゴリ（推測）` — no i18n changes required
- Feature 014 `store_name` out of scope — merchant LLM uses `description` only until then
- Memory invalid codes fall back to `classify_expense` via existing `resolve_code()` unknown handling
