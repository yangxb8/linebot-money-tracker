# Tasks: Item-Level Category Memory for Receipts

**Input**: Design documents from `/specs/018-item-category-memory/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included (constitution Test-First + plan pytest focus). Write tests first; ensure they fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Bot services at repo root: `services/`, `tests/`, `scripts/`, `supabase/migrations/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align repo artifacts and migration scaffold for 018

- [ ] T001 Confirm feature docs present under `specs/018-item-category-memory/` (plan.md, research.md, data-model.md, contracts/, quickstart.md) and `.specify/feature.json` points at this feature
- [ ] T002 [P] Add migration stub `supabase/migrations/20260714140000_category_item_memory.sql` from `specs/018-item-category-memory/contracts/supabase-schema-delta.md` (table + indexes + expenses.category_source check; do not apply remotely until polish)
- [ ] T003 [P] Add empty module stubs `services/item_normalize.py` and `scripts/backfill_category_item_memory.py` with module docstrings referencing contracts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema + core item identity/memory APIs required by every receipt story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Finalize DDL in `supabase/migrations/20260714140000_category_item_memory.sql` per `contracts/supabase-schema-delta.md` (partial unique indexes, kind/merchant CHECK, service_role grants, safe drop/recreate of `expenses_category_source_check`)
- [ ] T005 [P] Implement `normalize_item_key()` and generic denylist in `services/item_normalize.py` per `contracts/item-normalize.md` (build on `services/receipt_parser.clean_receipt_description`)
- [ ] T006 [P] Write failing tests for item key normalization in `tests/test_item_normalize.py` (planter/toilet-paper fixtures, generic → None, size/pack strip)
- [ ] T007 Implement item-memory repository helpers in `services/category_memory.py`: `lookup_item_memory`, `upsert_item_llm_seed` (store_item only), `record_item_user_correction` (store_item + item_only), `apply_item_silent_confirm` (store_item only) per `data-model.md`
- [ ] T008 [P] Write failing tests for item-memory write gates in `tests/test_category_item_memory.py` (LLM never writes item_only; correction writes both; weight ≥ 1.0 semantics)
- [ ] T009 Extend `CategoryResultWithProvenance` in `services/categorize.py` with `source` including `item_memory`, plus optional `item_key` / `item_memory_kind` fields per `contracts/categorize-item-memory.md`
- [ ] T010 Allow `category_source='item_memory'` through `services/expense_repository.py` insert/build paths (types + persistence payload)

**Checkpoint**: Foundation ready — normalize + item memory APIs + provenance types in place

---

## Phase 3: User Story 1 — Mixed-store receipt different categories (Priority: P1) 🎯 MVP

**Goal**: Receipt/image lines use item-memory mode with per-line classify + merchant soft prior (no merchant hard-skip), so mixed carts can get distinct categories.

**Independent Test**: Mocked two-item home-center receipt with merchant memory saying one category; lines still may receive different LLM categories; confirmation can show multiple category paths; text path unchanged when `memory_mode=merchant`.

### Tests for User Story 1

- [ ] T011 [P] [US1] Add failing tests in `tests/test_categorize_item_memory.py` for `memory_mode='item'`: merchant hard-skip must not apply; soft prior passed to classify; missing item_key still classifies
- [ ] T012 [P] [US1] Add failing tests in `tests/test_message_handler.py` (or new `tests/test_message_handler_item_memory.py`) asserting image pipeline calls classify with `memory_mode='item'` and text pipeline uses default `merchant`

### Implementation for User Story 1

- [ ] T013 [US1] Add optional `category_hint` to `classify_expense()` prompt in `services/categorize.py` per research Decision 4 / contracts
- [ ] T014 [US1] Implement `memory_mode='item'` branch in `classify_expense_with_memory()` in `services/categorize.py`: resolve merchant + item_key; on miss call classify with merchant soft prior; upsert store_item LLM seed only; never merchant hard-skip
- [ ] T015 [US1] Pass `memory_mode='item'` from image/receipt enrich path in `services/message_handler.py` (`_enrich_and_persist_items` / image success path); keep text path default `merchant`
- [ ] T016 [US1] Persist `category_source='item_memory'|'llm'` correctly for receipt lines in `services/message_handler.py` via existing insert row builder
- [ ] T017 [US1] Make T011–T012 tests pass; add structured log on soft-prior miss vs item hit in `services/categorize.py`

**Checkpoint**: Mixed receipt cold-start no longer forces one merchant category onto all lines (MVP)

---

## Phase 4: User Story 2 — Learned store+item rematch skips LLM (Priority: P1)

**Goal**: High-confidence store_item memory rematches the same product at the same store without category LLM.

**Independent Test**: Seed store_item weight ≥ 1.0 for (store X, item A); classify receipt line → `source=item_memory`, classify_expense not called; different item at store X still classifies.

### Tests for User Story 2

- [ ] T018 [P] [US2] Extend `tests/test_categorize_item_memory.py` with failing cases: weight ≥ 1.0 store_item hit skips LLM; weight < 1.0 falls through; two different items at same store use distinct memories

### Implementation for User Story 2

- [ ] T019 [US2] Complete store_item lookup + skip path in `services/categorize.py` (`source='item_memory'`, empty alternatives)
- [ ] T020 [US2] Implement store_item silent confirm (+0.5) in `services/categorize.py` / `services/category_memory.py` using prior expense with same store+item identity (`exclude_source_message_id`)
- [ ] T021 [US2] Make T018 tests pass; assert no `item_only` row created on LLM/silent paths in `tests/test_category_item_memory.py`

**Checkpoint**: Repeat product at same store skips categorize when confident

---

## Phase 5: User Story 4 — Reply-edit teaches only that item (Priority: P1)

**Goal**: Category reply-edit on a receipt line updates that line’s item memory only; does not rewrite merchant-only memory for the store.

**Independent Test**: Two-line receipt confirmation; edit line 2 category → store_item + item_only for item 2 only; `category_merchant_memory` for store unchanged; later different product at store not forced to edited category.

### Tests for User Story 4

- [ ] T022 [P] [US4] Extend `tests/test_reply_edit.py` with failing cases: receipt lineage (`metadata.store_name`) triggers `record_item_user_correction` and skips merchant `record_user_correction`; unrelated item memory untouched

### Implementation for User Story 4

- [ ] T023 [US4] Branch category-correction hooks in `services/reply_edit.py` to call `record_item_user_correction` when expense has `metadata.store_name`; do not call merchant `record_user_correction` on that path
- [ ] T024 [US4] Ensure bulk category change in `services/reply_edit.py` applies the same per-expense receipt vs text rule
- [ ] T025 [US4] Make T022 tests pass in `tests/test_reply_edit.py`; assert correction `weight=1.0` / `last_source=user_correction` for both memory_kinds when store known via `services/category_memory.py`

**Checkpoint**: Single-line receipt correction cannot poison whole-store merchant memory

---

## Phase 6: User Story 3 — Cross-store item-only reuse (Priority: P2)

**Goal**: item_only memory from explicit correction applies at other stores when store_item miss; LLM seeds never create item_only.

**Independent Test**: Correction at store A creates item_only; receipt at store B with same item_key and no store_item → item_memory hit; LLM-only at A does not affect B.

### Tests for User Story 3

- [ ] T026 [P] [US3] Extend `tests/test_categorize_item_memory.py` with failing cases: item_only hit after correction; store_item preferred over item_only; LLM seed does not create item_only affecting other store

### Implementation for User Story 3

- [ ] T027 [US3] Ensure lookup order store_item → item_only in `services/categorize.py` returns item_only hits with `source='item_memory'` and weight ≥ 1.0 skip
- [ ] T028 [US3] Verify `record_item_user_correction` in `services/category_memory.py` always upserts item_only; LLM/silent/backfill helpers never touch item_only
- [ ] T029 [US3] Make T026 tests pass in `tests/test_categorize_item_memory.py`

**Checkpoint**: Cross-store commodity reuse works for trusted corrections only

---

## Phase 7: User Story 5 — Text expenses keep merchant memory (Priority: P2)

**Goal**: Free-text expenses continue to use 013 merchant-only memory; item mode is not applied.

**Independent Test**: Starbucks/Uber-style text tests still pass; `memory_mode` remains `merchant`; no item_memory writes from text path.

### Tests for User Story 5

- [ ] T030 [P] [US5] Extend `tests/test_categorize_memory.py` / `tests/test_message_handler.py` asserting text path still uses merchant memory hit/skip and does not call item-memory lookup

### Implementation for User Story 5

- [ ] T031 [US5] Confirm text enrich path in `services/message_handler.py` never passes `memory_mode='item'`; leave 013 merchant flow intact in `services/categorize.py`
- [ ] T032 [US5] Make T030 + existing merchant regression tests pass (`python3 -m pytest -q tests/test_categorize_memory.py tests/test_message_handler.py`)

**Checkpoint**: Text merchant memory regression suite green

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Backfill, migration apply, docs, full verification

- [ ] T033 Implement `scripts/backfill_category_item_memory.py` (dry-run + apply; expenses with `metadata.store_name` only; store_item last-writer; never item_only) per plan/quickstart
- [ ] T034 [P] Add `tests/test_backfill_category_item_memory.py` covering dry-run counting and item_only-not-written assertion (mocked Supabase)
- [ ] T035 Apply migration to Supabase project (SQL editor or CLI) from `supabase/migrations/20260714140000_category_item_memory.sql` and verify `\d category_item_memory` + expenses check constraint
- [ ] T036 [P] Update `specs/018-item-category-memory/quickstart.md` with any final command/constraint-name fixes discovered during apply
- [ ] T037 Run full targeted pytest suite: `python3 -m pytest -q tests/test_item_normalize.py tests/test_category_item_memory.py tests/test_categorize_item_memory.py tests/test_categorize_memory.py tests/test_reply_edit.py tests/test_message_handler.py tests/test_backfill_category_item_memory.py`
- [ ] T038 Manual smoke per `specs/018-item-category-memory/quickstart.md` (image mixed receipt + reply-edit + text Starbucks) when `GEMINI_API_KEY` + Supabase creds available; record results in PR notes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: After Foundational — MVP
- **US2 (Phase 4)**: After US1 skip/seed plumbing (shares categorize item branch)
- **US4 (Phase 5)**: After Foundational item correction APIs (T007); ideally after US1 so receipt lineage exists end-to-end
- **US3 (Phase 6)**: After US4 correction writes item_only (or T007 correction helper + US1 lookup)
- **US5 (Phase 7)**: After US1 wiring (to prove text not switched); can run parallel with US2–US4 once T015 exists
- **Polish (Phase 8)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: Foundation only — MVP
- **US2 (P1)**: Builds on US1 item-mode classify branch
- **US4 (P1)**: Foundation correction APIs + receipt expenses; pairs with US2 learning
- **US3 (P2)**: Needs US4 (or T007+T023) for item_only rows from corrections
- **US5 (P2)**: Regression; depends on message_handler memory_mode wiring from US1

### Parallel Opportunities

- T002 || T003 (Setup)
- T005 || T006; T007 depends on T004/T005 conceptually for keys; T008 || after T007 interface sketched
- Within US1: T011 || T012 before T013–T016
- US5 tests (T030) can proceed beside US2/US3 once T015 done
- T034 || T036 in Polish after T033

---

## Parallel Example: User Story 1

```bash
# Tests first (fail):
Task: "T011 failing categorize item-mode tests in tests/test_categorize_item_memory.py"
Task: "T012 failing message_handler memory_mode tests"

# Then implement:
Task: "T013 category_hint in services/categorize.py"
Task: "T014 memory_mode=item branch in services/categorize.py"
Task: "T015 message_handler passes memory_mode=item for images"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundation
2. Phase 3 US1 (soft prior + no merchant hard-skip on receipts)
3. **STOP and VALIDATE** with mocked two-item receipt tests
4. Demo mixed-cart fix before learning/skip polish

### Incremental Delivery

1. US1 → cold-start mixed categories  
2. US2 → rematch skip  
3. US4 → safe corrections  
4. US3 → cross-store item_only  
5. US5 → text regression lock  
6. Polish → backfill + migration apply + quickstart smoke  

### Suggested MVP scope

**US1 only** (T001–T017): stops all-lines-same-category on receipt photos.

---

## Notes

- [P] = different files / no wait on incomplete sibling
- Apply remote migration (T035) only after SQL review; local tests can mock Supabase
- Do not enable RLS on `category_item_memory` without deny policies (same as 013 merchant table)
- Commit after each task or logical group; keep text merchant path green continuously
