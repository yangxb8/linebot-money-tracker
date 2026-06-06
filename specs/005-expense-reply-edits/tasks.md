# Tasks: Expense Reply Edits

**Input**: Design documents from `/specs/005-expense-reply-edits/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; **004-supabase-expense-storage** implemented on branch baseline

**Organization**: Tasks grouped by user story. **MVP = User Stories 4 + 1 + 2 + 3** (linkage + category + field edits + soft-delete/restore).

**Tests**: Included per constitution Test-First Delivery and plan.md testing strategy.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to spec user stories (US1–US5)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Reply context types and LINE event extraction for reply-to-message flow

- [X] T001 [P] Extend `services/message_context.py` with `ReplyContext` dataclass (`line_user_id`, `user_reply_message_id`, `quoted_bot_message_id`) per `specs/005-expense-reply-edits/data-model.md`
- [X] T002 [P] Add `extract_quoted_message_id()` to `services/line_event.py` per `specs/005-expense-reply-edits/research.md` R1

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema delta, confirmation repository, expense mutators, reply routing skeleton — MUST complete before user story phases

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create `supabase/migrations/20260606130000_expense_reply_edits.sql` with `deleted_at`/`updated_at` on `expenses`, tables `confirmation_messages`, `confirmation_expenses`, `reply_edit_audit`, `processed_reply_messages`, and patched rollup RPCs per `specs/005-expense-reply-edits/contracts/supabase-schema-delta.md`
- [X] T004 Apply migration to `https://nyuenufldaqsjybjhawl.supabase.co` via Supabase MCP `apply_migration` (server `project-0-linebot-money-tracker-supabase`); verify with `list_tables`
- [X] T005 [P] Implement `services/confirmation_repository.py` with `save_confirmation`, `get_confirmation_by_bot_message_id`, `set_pending_action`, `try_mark_reply_processed`, and `write_audit` per `specs/005-expense-reply-edits/contracts/confirmation-linkage.md`
- [X] T006 [P] Extend `services/expense_repository.py` with `update_expense_fields`, `soft_delete_expenses`, `restore_expenses`, and `get_expenses_by_ids` per `specs/005-expense-reply-edits/contracts/expense-mutation.md`
- [X] T007 [P] Add unit tests for confirmation save/load and reply idempotency in `tests/test_confirmation_repository.py` (mock Supabase — no dynamic SQL)
- [X] T008 [P] Add unit tests for expense soft-delete, restore, and field update mutators in `tests/test_expense_repository_mutations.py`
- [X] T009 Add reply routing stub in `services/message_handler.py`: `process_reply_edit()` entry point and dispatch from `main.py` when `quoted_bot_message_id` is present

**Checkpoint**: Migration live; repositories callable; webhook routes reply events to stub handler

---

## Phase 3: User Story 4 - Link User Replies to Confirmation (Priority: P1) 🎯 MVP (part 1)

**Goal**: Persist bot confirmation message ID + text snapshot + expense links after each expense log; load confirmation on user reply-to-message

**Independent Test**: Log expense → row in `confirmation_messages` with `bot_message_id`; reply with matching `quotedMessageId` loads same confirmation; reply to unknown ID returns guidance without DB mutation

### Tests for User Story 4

- [X] T010 [P] [US4] Add handler tests for confirmation save after log and unknown-confirmation reply in `tests/test_message_handler_reply.py`

### Implementation for User Story 4

- [X] T011 [US4] Capture `SentMessage.id` from `ReplyMessageResponse` in `main.py` helper wrapping `reply_message`
- [X] T012 [US4] After successful expense log in `services/message_handler.py`, call `confirmation_repository.save_confirmation()` with `items_snapshot` (including category alternatives) per `specs/005-expense-reply-edits/contracts/confirmation-linkage.md`
- [X] T013 [US4] Implement confirmation load + ownership check in `process_reply_edit()` when `ReplyContext.quoted_bot_message_id` is set in `services/message_handler.py`
- [X] T014 [US4] Return FR-010 guidance when reply targets unknown or non-confirmation message in `services/message_handler.py`
- [X] T015 [US4] Print `bot_message_id` to stdout in `local_run.py` after log for console `--reply-to` testing per `specs/005-expense-reply-edits/quickstart.md`

**Checkpoint**: Confirmations persisted; reply-to-known-confirmation loads context

---

## Phase 4: User Story 1 - Change Category by Reply (Priority: P1) 🎯 MVP (part 2)

**Goal**: User replies to confirmation to pick numbered alternative or natural-language category; stored expense category updates

**Independent Test**: Single-item log → reply `2` → category matches alternative 2; multi-item bare `2` → clarification prompt, no change

### Tests for User Story 1

- [X] T016 [P] [US1] Add unit tests for EditIntent JSON validation, numbered category pick resolution, and multi-item bare-number clarify in `tests/test_reply_edit.py`

### Implementation for User Story 1

- [X] T017 [US1] Implement `services/reply_edit.py` with `parse_edit_intent()` (Gemini JSON + jsonschema) per `specs/005-expense-reply-edits/contracts/reply-edit-intent.md` and `contracts/llm-reply-edit-boundary.md`
- [X] T018 [US1] Implement `resolve_category_pick()` using `items_snapshot` alternatives (single-item bare 1–3; multi-item requires item id) in `services/reply_edit.py`
- [X] T019 [US1] Wire category-only apply path: `update_expense_fields(category_code=...)` with denormalized IDs in `services/reply_edit.py` called from `process_reply_edit()` in `services/message_handler.py`
- [X] T020 [US1] Update confirmation `items_snapshot` category fields after successful category edit in `services/reply_edit.py` or `confirmation_repository.py`

**Checkpoint**: Category correction via reply works for single- and multi-item (with item identification)

---

## Phase 5: User Story 2 - Edit Amount, Description, or Date by Reply (Priority: P1) 🎯 MVP (part 3)

**Goal**: User corrects amount, description, currency, or expense date via natural-language reply; atomic multi-field updates

**Independent Test**: Reply "actually 3800 yen" → only amount changes; invalid amount → no partial update + explanation

### Tests for User Story 2

- [X] T021 [P] [US2] Add unit tests for field update apply path, validation failures, and atomic multi-field update in `tests/test_reply_edit.py`

### Implementation for User Story 2

- [X] T022 [US2] Extend `parse_edit_intent()` prompt and schema for amount, description, currency, expense_date updates in `services/reply_edit.py`
- [X] T023 [US2] Implement field update apply with JST date parsing and validation (no partial updates on failure) in `services/reply_edit.py`
- [X] T024 [US2] Integrate combined category + field updates in single reply in `services/reply_edit.py`

**Checkpoint**: All editable expense fields except delete/restore updatable via reply

---

## Phase 6: User Story 3 - Delete and Restore by Reply (Priority: P1) 🎯 MVP (part 4)

**Goal**: Soft-delete, restore, delete-all with confirmation, restore-all via reply

**Independent Test**: Reply delete → `deleted_at` set, excluded from rollup; reply restore → active again; delete-all requires YES; restore-all restores all soft-deleted on confirmation

### Tests for User Story 3

- [X] T025 [P] [US3] Add tests for soft-delete, restore, delete-all confirm flow, and restore-all in `tests/test_reply_edit.py` and `tests/test_message_handler_reply.py`

### Implementation for User Story 3

- [X] T026 [US3] Implement `soft_delete` and `restore` single-target apply paths in `services/reply_edit.py`
- [X] T027 [US3] Implement delete-all pending flow: set `pending_action='delete_all'`, prompt user; on `confirm_pending` execute bulk soft-delete in `services/reply_edit.py`
- [X] T028 [US3] Implement restore-all immediate apply path in `services/reply_edit.py`
- [X] T029 [US3] Handle edge cases: no active expenses to edit, restore when nothing deleted, multi-item delete without item ref in `services/reply_edit.py`

**Checkpoint**: Full delete/restore lifecycle with soft-delete semantics

---

## Phase 7: User Story 5 - Bot Summarizes Actions (Priority: P2)

**Goal**: Every reply edit produces language-matched before/after summary; audit log written

**Independent Test**: Category change summary shows old and new paths in user's reply language; failed edit explains why

### Tests for User Story 5

- [X] T030 [P] [US5] Add unit tests for JP/EN/ZH summary formatting and clarification messages in `tests/test_reply_summary.py`

### Implementation for User Story 5

- [X] T031 [US5] Implement `services/reply_summary.py` with `detect_reply_language()` and `format_edit_result()` per FR-009 and FR-015
- [X] T032 [US5] Integrate summary formatting and `write_audit()` on every `process_reply_edit()` outcome in `services/message_handler.py`
- [X] T033 [US5] Ensure storage failures during edit return friendly message without crashing webhook in `services/message_handler.py`

**Checkpoint**: All reply outcomes produce explicit user-facing summary + audit row

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Console harness, docs, regression safety

- [X] T034 [P] Add `--reply-to` flag and reply simulation to `local_run.py` per `specs/005-expense-reply-edits/quickstart.md`
- [X] T035 [P] Update root `README.md` with expense reply-edit section linking to `specs/005-expense-reply-edits/quickstart.md`
- [X] T036 [P] Update `specs/004-supabase-expense-storage/contracts/categorization-reply.md` footer to note corrections persist via feature 005 (doc cross-link only)
- [X] T037 Run full test suite `python -m pytest -q` and fix regressions
- [X] T038 [P] Manual validation of `specs/005-expense-reply-edits/quickstart.md` against live Supabase project `nyuenufldaqsjybjhawl`
- [X] T039 Mark completed tasks `[X]` in this file after implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US4 (Phase 3)**: Depends on Phase 2 — **BLOCKS US1–US3** (linkage required)
- **US1 (Phase 4)**: Depends on Phase 3
- **US2 (Phase 5)**: Depends on Phase 4 (shared `reply_edit.py` pipeline)
- **US3 (Phase 6)**: Depends on Phase 4 (shared apply framework); can parallel with US2 only after T017–T019 if carefully coordinated — **recommended sequential US2 → US3**
- **US5 (Phase 7)**: Depends on US1–US3 apply paths existing
- **Polish (Phase 8)**: Depends on US5 (or MVP US4+US1–US3 for minimal polish)

### User Story Dependencies

| Story | Depends on | Notes |
| ----- | ---------- | ----- |
| US4 | Foundational | Confirmation save + reply detect |
| US1 | US4 | Category pick from snapshot |
| US2 | US1 | Extends same EditIntent apply path |
| US3 | US1 | Delete/restore uses same pipeline |
| US5 | US1–US3 | Summaries for all action types |

### Parallel Opportunities

**Phase 1**: T001, T002 in parallel

**Phase 2** (after T003 file exists): T005, T006, T007, T008 in parallel; T004 after T003; T009 after T005 stub

**Phase 3**: T010 parallel before T011–T014

**Phase 4**: T016 before T017; T018–T020 sequential after T017

**Phase 5–6**: T021–T024 sequential; T025 parallel with T026 prep; T026–T029 sequential

**Phase 7**: T030 parallel with T031 prep

**Phase 8**: T034, T035, T036, T038 in parallel

---

## Parallel Example: Foundational Phase

```bash
# After T003 migration file exists:
Task T005: services/confirmation_repository.py
Task T006: services/expense_repository.py mutators
Task T007: tests/test_confirmation_repository.py
Task T008: tests/test_expense_repository_mutations.py
# Then T004 apply migration, T009 routing stub
```

## Parallel Example: User Story 1

```bash
Task T016: tests/test_reply_edit.py (category tests)
# Then sequentially: T017 → T018 → T019 → T020
```

---

## Implementation Strategy

### MVP First (User Stories 4 + 1 + 2 + 3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**apply migration**)
3. Complete Phase 3: US4 — confirmation linkage
4. Complete Phase 4: US1 — category reply edits
5. Complete Phase 5: US2 — field reply edits
6. Complete Phase 6: US3 — soft-delete / restore / delete-all / restore-all
7. **STOP and VALIDATE**: `local_run.py --text "..."` then `--reply-to <id> --text "2"` → category updated + summary
8. Phase 7 (US5) for polished summaries; Phase 8 for production docs

### Incremental Delivery

1. Setup + Foundational → schema + repositories + routing
2. US4 → confirmations saved and loadable
3. US1 → category corrections work
4. US2 → amount/description/date corrections
5. US3 → delete/restore flows
6. US5 → multilingual summaries + audit
7. Polish → console `--reply-to`, README, full pytest

### LLM / DB Boundary (all phases)

- Gemini outputs **EditIntent JSON only** for reply parsing
- App validates and calls **fixed repository methods** (`update_expense_fields`, `soft_delete_expenses`, `restore_expenses`, confirmation CRUD)
- User-facing summaries from **`reply_summary.py`**, not LLM SQL
- See `specs/005-expense-reply-edits/contracts/llm-reply-edit-boundary.md`

---

## Notes

- Supabase MCP server: `project-0-linebot-money-tracker-supabase`
- Requires 004 expense logging + categorization confirmation reply format (numbered alternatives in snapshot)
- LINE reply uses `quotedMessageId` inbound; bot confirmation ID from `ReplyMessageResponse.sent_messages[0].id`
- Deferred from spec: edit via non-reply messages, hard delete, budget impact in summaries
