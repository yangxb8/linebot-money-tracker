---
description: "Task list for Receipt Store Name Extraction feature implementation"
---

# Tasks: Receipt Store Name Extraction

**Input**: Design documents from `/specs/014-receipt-store-name/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; features **004**, **013** complete

**Tests**: pytest included per plan.md constitution compliance (vision parse, store_name unify, merchant skip/fallback, metadata persist, backfill/reply-edit preference). Manual quickstart in Polish.

**Organization**: Tasks grouped by user story. User Story 2 (OCR) deferred to 014 v2 — no v1 tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm dependencies and feature context before schema work

- [ ] T001 Verify features **013** and **004** are deployed locally per `specs/014-receipt-store-name/quickstart.md` prerequisites (`category_merchant_memory`, expense insert pipeline)
- [ ] T002 [P] Confirm `data/merchant_aliases_ja.yaml` includes supermarket keys used in SC-001 spot checks (e.g. `aeon`, `seven_eleven`) in `data/merchant_aliases_ja.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `expenses.metadata` jsonb column and repository support — MUST complete before User Story 1

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create Supabase migration `supabase/migrations/20260629120000_expense_metadata.sql` per `specs/014-receipt-store-name/contracts/supabase-schema-delta.md` (`metadata jsonb NOT NULL DEFAULT '{}'`)
- [ ] T004 [P] Add `metadata: dict` field to `ExpenseInsertRow` dataclass in `services/expense_repository.py`
- [ ] T005 [P] Update `_row_to_dict()` in `services/expense_repository.py` to serialize `metadata` for Supabase jsonb insert
- [ ] T006 Extend `build_insert_row()` in `services/expense_repository.py` to default `metadata={}` when item has no `store_name`

**Checkpoint**: Foundation ready — migration defined, expense rows accept metadata dict

---

## Phase 3: User Story 1 — Grocery receipt uses store for all lines (Priority: P1) 🎯 MVP

**Goal**: LLM vision receipts propagate receipt-level `store_name` to all lines, skip merchant LLM when store normalizes, persist raw store in `metadata`, text expenses unchanged

**Independent Test**: `python local_run.py --image path/to/multi_line_receipt.jpg` → all lines share `metadata.store_name`; usage logs show no `merchant_extract` per line when store normalizes; `python local_run.py --text "..."` unchanged

### Tests for User Story 1

- [ ] T007 [P] [US1] Create `tests/test_receipt_store_name.py` for `propagate_receipt_store_name()` (unify all lines, null when absent, null when inconsistent)
- [ ] T008 [P] [US1] Extend `tests/test_ai_assist.py` to validate vision parse accepts optional top-level `store_name` in `services/ai_assist.py`
- [ ] T009 [P] [US1] Create `tests/test_merchant_resolve.py` asserting `resolve_raw_merchant()` skips `extract_merchant_name` when store normalizes and falls back when normalize returns null
- [ ] T010 [P] [US1] Extend `tests/test_categorize_memory.py` for store_name path through `classify_expense_with_memory()` in `services/categorize.py`

### Implementation for User Story 1 — Vision parse & propagate

- [ ] T011 [P] [US1] Implement `propagate_receipt_store_name()` in `services/receipt_store_name.py` per `specs/014-receipt-store-name/contracts/receipt-vision-parse.md`
- [ ] T012 [US1] Extend `_RECEIPT_IMAGE_PROMPT`, `RECEIPT_IMAGE_PARSE_SCHEMA`, and `ReceiptImageParseResult` with optional `store_name` in `services/ai_assist.py`
- [ ] T013 [US1] Update `validate_receipt_image_parse()` in `services/ai_assist.py` to pass through `store_name` on `ReceiptImageParseResult`
- [ ] T014 [US1] Wire `propagate_receipt_store_name()` in `services/message_handler.py` `_extract_expense_items_from_image()` after `_prepare_llm_receipt_items()`

### Implementation for User Story 1 — Merchant resolution

- [ ] T015 [P] [US1] Implement `resolve_raw_merchant()` in `services/merchant_resolve.py` per `specs/014-receipt-store-name/contracts/merchant-resolution.md`
- [ ] T016 [US1] Replace inline `extract_merchant_name` call with `resolve_raw_merchant()` in `classify_expense_with_memory()` in `services/categorize.py`
- [ ] T017 [P] [US1] Add INFO logging for `store_name` vs `description` merchant source in `services/merchant_resolve.py`

### Implementation for User Story 1 — Persistence & handler integration

- [ ] T018 [US1] Set `metadata={"store_name": item["store_name"]}` in `build_insert_row()` when item has non-empty `store_name` in `services/expense_repository.py`
- [ ] T019 [P] [US1] Create `tests/test_expense_repository_metadata.py` asserting insert row includes `metadata.store_name` when item dict has store_name
- [ ] T020 [US1] Extend `tests/test_message_handler.py` to assert image pipeline items carry unified `store_name` after mocked `assist_parse_image`
- [ ] T021 [US1] Verify text path in `services/message_handler.py` `_extract_expense_items_from_text()` leaves items without `store_name` (acceptance scenario 3)

### Implementation for User Story 1 — Backfill & reply-edit (FR-006)

- [ ] T022 [P] [US1] Implement `merchant_key_from_expense_row()` preferring `metadata.store_name` in `services/merchant_resolve.py`
- [ ] T023 [US1] Update `scripts/backfill_category_memory.py` to select `metadata` column and use `merchant_key_from_expense_row()` for grouping
- [ ] T024 [P] [US1] Create `tests/test_backfill_category_memory.py` asserting backfill prefers `metadata.store_name` over product description
- [ ] T025 [US1] Add optional `store_name` parameter to `record_user_correction_from_description()` in `services/category_memory.py` using `resolve_raw_merchant()` rules
- [ ] T026 [US1] Load expense `metadata.store_name` and pass to correction hook in `services/reply_edit.py` `_record_category_memory_correction()`
- [ ] T027 [P] [US1] Extend `tests/test_reply_edit.py` to assert category correction uses store_name from expense metadata when present
- [ ] T028 [US1] Update `find_prior_expense_for_merchant()` in `services/category_memory.py` to match rows using `metadata.store_name` via `merchant_key_from_expense_row()`

**Checkpoint**: User Story 1 complete — vision receipts share store merchant_key, metadata persisted, backfill/reply-edit prefer store_name, text path unchanged

---

## Phase 4: User Story 2 — OCR register receipts (Priority: P2) ⏸️ Deferred 014 v2

**Goal**: OCR `receipt_parser` header heuristics set `store_name` on text/OCR path

**Status**: **Not in 014 v1 scope** per spec clarifications. No tasks generated. Re-run `/speckit-tasks` after 014 v2 spec update.

**Future work** (reference only):
- Header heuristic in `services/receipt_parser.py`
- Wire through same `propagate_receipt_store_name()` and `resolve_raw_merchant()` pipeline

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Validation, regression, and success-criteria spot checks

- [ ] T029 [P] Run pytest for all 014-related tests: `tests/test_receipt_store_name.py`, `tests/test_merchant_resolve.py`, `tests/test_ai_assist.py`, `tests/test_categorize_memory.py`, `tests/test_expense_repository_metadata.py`, `tests/test_backfill_category_memory.py`, `tests/test_reply_edit.py`, `tests/test_message_handler.py`
- [ ] T030 Validate manual flow in `specs/014-receipt-store-name/quickstart.md` using `python local_run.py --image path/to/receipt.jpg` and SQL checks for `metadata->>'store_name'`
- [ ] T031 [P] Spot-check SC-001: log multi-line vision receipt at known chain; confirm ≥70% of lines share store-derived `merchant_key` in `category_merchant_memory` (manual SQL per quickstart)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS User Story 1**
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Deferred — do not start in v1
- **Polish (Phase 5)**: Depends on User Story 1 completion

### User Story Dependencies

- **User Story 1 (P1)**: Only active story in v1; no dependency on US2
- **User Story 2 (P2)**: Deferred to 014 v2; blocked on future spec/plan update

### Within User Story 1

Recommended order:
1. Tests T007–T010 (fail before impl)
2. T011–T014 vision parse pipeline
3. T015–T017 merchant resolution (depends on T011 for item shape)
4. T018–T021 persistence + handler (depends on T003–T006, T014)
5. T022–T028 backfill/reply-edit (depends on T015, T018)

### Parallel Opportunities

- **Phase 1**: T002 parallel with T001
- **Phase 2**: T004 ∥ T005 after T003 migration file created
- **Phase 3 tests**: T007 ∥ T008 ∥ T009 ∥ T010
- **Phase 3 impl**: T011 ∥ T015 (different new files); T019 ∥ T024 ∥ T027 (different test files)
- **Phase 5**: T029 ∥ T031 after US1 complete

---

## Parallel Example: User Story 1

```bash
# Tests first (parallel):
pytest tests/test_receipt_store_name.py      # T007
pytest tests/test_merchant_resolve.py        # T009
pytest tests/test_ai_assist.py -k store_name # T008

# Core modules (parallel after tests written):
# services/receipt_store_name.py             # T011
# services/merchant_resolve.py               # T015

# Integration (sequential):
# services/ai_assist.py → message_handler.py → categorize.py → expense_repository.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (migration + metadata on expense rows)
3. Complete Phase 3: User Story 1 (vision → merchant → persist → 013 hooks)
4. **STOP and VALIDATE**: quickstart manual test + pytest
5. Deploy when SC-001 spot check passes

### Incremental Delivery

| Increment | Delivers | Validate |
| --------- | -------- | -------- |
| Foundational | `metadata` column + repo | migration apply |
| Vision parse | store_name on item dicts | T007–T014 tests |
| Merchant skip | fewer LLM calls on receipts | T009–T016 tests |
| Persistence | DB audit trail | T018–T019 tests |
| FR-006 hooks | backfill + reply-edit | T022–T028 tests |

### Parallel Team Strategy

With two developers after Foundational:
- **Dev A**: Vision parse (T011–T014, T007–T008)
- **Dev B**: Merchant resolve + categorize (T015–T017, T009–T010)
- **Merge**: Persistence (T018–T021), then FR-006 (T022–T028)

---

## Notes

- User Story 2 (OCR heuristics) explicitly out of v1 — see Phase 4
- Raw `store_name` stored in metadata; normalization only for `merchant_key` (FR-004)
- Text and OCR assist paths must NOT set `store_name` until 014 v2
- Commit after each task group; apply migration before integration tests against Supabase
