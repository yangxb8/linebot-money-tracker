---
description: "Task list for Wish List feature implementation"
---

# Tasks: Wish List

**Input**: Design documents from `/specs/020-wish-list/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; features **009–015** baseline (dashboard, tenants, categories, expenses, budgets, budget pace)

**Tests**: Included per constitution Test-First Delivery and plan.md — pytest for bot wish intent / budget impact / confirm-add; Vitest for web validation helpers. Manual quickstart checklist in Polish.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Bot: `services/`, `tests/`, `local_run.py` at repository root
- Web: `web/src/`
- Schema: `supabase/migrations/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module scaffolding, types, and i18n placeholders for wish list

- [ ] T001 Create wish-list TypeScript types in `web/src/lib/wish-list/types.ts` per `specs/020-wish-list/data-model.md` and `contracts/wish-list-api.md` (WishListItem, WishListStatus, sort modes, execute payload)
- [ ] T002 [P] Add wish-list i18n key placeholders in `web/src/lib/i18n/messages.ts` (`navWishList`, CRUD labels, execute confirm, executed filter, wish tag, validation errors — ja/en/zh)
- [ ] T003 [P] Create empty bot module stubs `services/wish_list.py` and `services/wish_list_budget.py` with module docstrings referencing `contracts/wish-list-bot.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema migration and shared persistence/validation that MUST complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create Supabase migration `supabase/migrations/20260726120000_wish_list_items.sql` per `specs/020-wish-list/contracts/supabase-schema-delta.md` (`wish_list_items` table, indexes, `expenses.wish_list_item_id`, circular-FK-safe ordering, status check)
- [ ] T005 Apply migration to Supabase project `https://nyuenufldaqsjybjhawl.supabase.co` and verify `\d wish_list_items` plus `expenses.wish_list_item_id` (note result in `specs/020-wish-list/quickstart.md` if needed)
- [ ] T006 [P] Implement wish-list input validation in `web/src/lib/wish-list/validation.ts` (required name, amount > 0, category required, optional http(s) `product_url`)
- [ ] T007 [P] Implement server helpers in `web/src/lib/wish-list/server.ts` (list/create/update/soft-delete/reorder/fetch-by-id with `assertTenantAccess` from `web/src/lib/periodic/tenant-access.ts`, category denorm)
- [ ] T008 [P] Implement client helpers in `web/src/lib/wish-list/client.ts` wrapping `/api/wish-list` fetch calls with tenant params
- [ ] T009 [P] Implement Python repository helpers in `services/wish_list.py` (insert active item for tenant, list active — used by bot confirm path; share column conventions with web)
- [ ] T010 [P] Add Vitest coverage in `web/src/lib/wish-list/validation.test.ts` for name/amount/url validation cases from FR-018
- [ ] T011 Ensure `v_expenses_enriched` (or expense select paths in `web/src/lib/expenses/server.ts`) expose `wish_list_item_id` if the view is a hard column list

**Checkpoint**: Foundation ready — migration applied, web/bot persistence helpers and validation tests in place

---

## Phase 3: User Story 1 - Maintain an active wish list in the web app (Priority: P1) 🎯 MVP

**Goal**: Signed-in user can CRUD wish list items on a new page, reorder by priority, and sort by created time or price; list is per ledger via tenant switcher

**Independent Test**: Create three items with different prices/categories, reorder manually, switch sort to price, edit one, delete another, reload — persistence and ledger isolation hold

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T012 [P] [US1] Add Vitest/unit coverage for sort-order helpers (if extracted) or document API contract assertions for reorder payload in `web/src/lib/wish-list/validation.test.ts`

### Implementation for User Story 1

- [ ] T013 [P] [US1] Implement `GET` and `POST` in `web/src/app/api/wish-list/route.ts` per `contracts/wish-list-api.md` (default `status=active`, sort query params)
- [ ] T014 [P] [US1] Implement `PATCH` and `DELETE` in `web/src/app/api/wish-list/[id]/route.ts` (active-only update/soft-delete)
- [ ] T015 [P] [US1] Implement `POST` in `web/src/app/api/wish-list/reorder/route.ts` (`ordered_ids` → rewrite `sort_order`)
- [ ] T016 [P] [US1] Create `web/src/components/wish-list/WishListItemForm.tsx` (name, amount, category picker, optional product URL, validation errors)
- [ ] T017 [P] [US1] Create `web/src/components/wish-list/WishListActiveList.tsx` (priority reorder controls, sort mode toggle: priority/created/price, edit/delete actions)
- [ ] T018 [US1] Create `web/src/components/wish-list/WishListPage.tsx` with `TenantSwitcher`, empty state, fetch on tenant change, wire form + active list
- [ ] T019 [US1] Create `web/src/app/(app)/wish-list/page.tsx` rendering `WishListPage`
- [ ] T020 [P] [US1] Add `navWishList` entry to `NAV_ITEMS` in `web/src/components/SideDrawer.tsx`
- [ ] T021 [US1] Add `/wish-list` route title branch in `web/src/components/AppShell.tsx`

**Checkpoint**: User Story 1 complete — web CRUD + priority + sort works per ledger

---

## Phase 4: User Story 2 - Execute a wish list item into an expense (Priority: P1)

**Goal**: From the web Wish List page, user confirms execute with editable fields (date default today); system creates expense with `wish_list_item_id`, marks item executed, removes from active list

**Independent Test**: Execute an item while changing amount/category/date; expense appears in history with confirmed values; item gone from active list

### Tests for User Story 2

- [ ] T022 [P] [US2] Add pytest or web-level test notes for execute conflict (already executed → 409) in `tests/test_wish_list_execute.py` OR extend validation tests; prefer pytest against repository helpers if execute shared in `services/wish_list.py`

### Implementation for User Story 2

- [ ] T023 [US2] Implement execute persistence in `web/src/lib/wish-list/server.ts` (insert expense with confirmed fields + `wish_list_item_id`; set item `status=executed` and `executed_expense_id`; reject non-active)
- [ ] T024 [US2] Implement `POST` in `web/src/app/api/wish-list/[id]/execute/route.ts` per `contracts/wish-list-api.md` (default `expense_date` today)
- [ ] T025 [P] [US2] Create `web/src/components/wish-list/WishListExecuteDialog.tsx` (pre-filled editable name/amount/category/date; confirm/cancel)
- [ ] T026 [US2] Wire Execute action from `WishListActiveList.tsx` / `WishListPage.tsx` to dialog + execute API; refresh active list on success; cancel leaves item unchanged
- [ ] T027 [US2] Add execute-related i18n strings in `web/src/lib/i18n/messages.ts`

**Checkpoint**: User Story 2 complete — web execute creates expense and clears active item

---

## Phase 5: User Story 3 - Add a wish list item from the LINE bot with budget impact (Priority: P1)

**Goal**: Bot detects not-yet-purchased intent, does not log expense, shows budget impact (remaining ± pace when ahead), yes/no confirm to add; group chat writes to group ledger

**Independent Test**: `python3 local_run.py --text "I want to buy headphones 15000 yen"` → impact + prompt, no expense; reply `yes` → item on web wish list; ordinary `Lunch 1200` still logs expense

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T028 [P] [US3] Add pytest for wish intent classification / phrase gate in `tests/test_wish_list_intent.py` (wish vs expense; EN/JA cues)
- [ ] T029 [P] [US3] Add pytest for `build_wish_list_budget_impact` in `tests/test_wish_list_budget.py` (remaining always when budgeted; pace only when ahead; no-budget messaging inputs)
- [ ] T030 [P] [US3] Add pytest for confirm/decline pending `wish_list_add` in `tests/test_wish_list_confirm.py` (yes inserts item, no does not; no expense rows)

### Implementation for User Story 3

- [ ] T031 [US3] Extend `TextMessageIntent` and `COMBINED_TEXT_INTENT_PROMPT` in `services/intent.py` with `wish_list` per `contracts/wish-list-bot.md`; add deterministic phrase gate for clear cues
- [ ] T032 [US3] Implement `build_wish_list_budget_impact` in `services/wish_list_budget.py` using `fetch_budget_summary` / pace helpers from `services/budget_pace.py` (hypothetical spent = spent + amount)
- [ ] T033 [US3] Implement wish-list reply formatting (templates and/or short LLM scope) in `services/wish_list.py` or adjacent module (candidate details + impact + yes/no ask; fail-open if budget RPC fails)
- [ ] T034 [US3] Branch `wish_list` intent in `services/message_handler.py` before expense persist: extract via assist parse, categorize, budget impact, save confirmation with `pending_action='wish_list_add'`
- [ ] T035 [US3] Handle affirm/cancel for `wish_list_add` in `services/reply_edit.py` (and `confirmation_repository.py` if pending_action enum/docs need update): yes → `services/wish_list.py` insert; no → clear pending
- [ ] T036 [US3] Extend `local_run.py` to allow `--image` together with `--text` and pass accompanying text into image processing for wish intent
- [ ] T037 [US3] Extend `process_image_message` in `services/message_handler.py` to accept optional accompanying text and route wish intent without expense insert
- [ ] T038 [US3] Verify ordinary expense path regression in `tests/test_wish_list_intent.py` or existing expense tests (messages without wish intent still persist expenses)

**Checkpoint**: User Story 3 complete — bot wish add with budget impact; expenses unchanged when no wish intent

---

## Phase 6: User Story 4 - Review executed wish list items (Priority: P2)

**Goal**: User filters Wish List page to executed items showing final expense values and a link to the related expense

**Independent Test**: After execute with changed amount, active list hides item; executed filter shows confirmed expense values + link

### Implementation for User Story 4

- [ ] T039 [US4] Extend `GET` in `web/src/app/api/wish-list/route.ts` / `server.ts` for `status=executed` to join expense summary fields per `contracts/wish-list-api.md`
- [ ] T040 [P] [US4] Create `web/src/components/wish-list/WishListExecutedList.tsx` (read-only rows: expense values + navigate/link to expense)
- [ ] T041 [US4] Add active/executed filter control on `WishListPage.tsx`; default active; empty executed state
- [ ] T042 [P] [US4] Add executed-filter i18n strings in `web/src/lib/i18n/messages.ts`

**Checkpoint**: User Story 4 complete — executed history visible without cluttering active priorities

---

## Phase 7: User Story 5 - Wish list tag on expense cards (Priority: P2)

**Goal**: Expense cards show a wish-list tag alongside category when `wish_list_item_id` is set

**Independent Test**: Wish-origin expense shows category + wish tag; normal expense shows no wish tag

### Implementation for User Story 5

- [ ] T043 [P] [US5] Add `wish_list_item_id` to `web/src/lib/expenses/types.ts` and ensure list fetch in `web/src/lib/expenses/server.ts` selects it
- [ ] T044 [US5] Render wish-list tag in `web/src/components/expenses/ExpenseRowItem.tsx` (pill style consistent with `ExpenseMerchantTag` / category tag) when `wish_list_item_id` is non-null
- [ ] T045 [P] [US5] Add wish-tag i18n label in `web/src/lib/i18n/messages.ts`

**Checkpoint**: User Story 5 complete — wish-origin expenses visually tagged in history

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end verification and documentation hygiene

- [ ] T046 [P] Run `python3 -m pytest -q` and fix regressions from wish-list bot changes
- [ ] T047 [P] Run `npm test` and `npm run lint` in `web/` and fix wish-list web issues
- [ ] T048 Walk through `specs/020-wish-list/quickstart.md` manual flows (web CRUD, execute, bot yes/no, group ledger) and update quickstart if commands drift
- [ ] T049 [P] Confirm `.specify/feature.json` and `.cursor/rules/specify-rules.mdc` still point at `specs/020-wish-list`
- [ ] T050 Code cleanup: ensure no expense insert on wish path; logging for wish intent / pending_action / execute outcomes in bot and API handlers

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: Depends on Foundational — 🎯 MVP
- **US2 (Phase 4)**: Depends on Foundational + US1 active list/UI entry points (execute from active list)
- **US3 (Phase 5)**: Depends on Foundational (`services/wish_list.py` insert); can proceed in parallel with US1/US2 after T009
- **US4 (Phase 6)**: Depends on US2 (executed rows exist)
- **US5 (Phase 7)**: Depends on US2 (`wish_list_item_id` on expenses)
- **Polish (Phase 8)**: Depends on all desired stories

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on other stories
- **US2 (P1)**: After US1 page/list (needs Execute entry point)
- **US3 (P1)**: After Foundational bot repository — independent of web UI except shared table
- **US4 (P2)**: After US2
- **US5 (P2)**: After US2

### Within Each User Story

- Tests (where listed) MUST be written and FAIL before implementation
- Persistence/helpers before API routes before UI
- Story complete before moving to next priority when sequencing solo

### Parallel Opportunities

- T001–T003 setup in parallel after types started
- T006–T011 foundational helpers/tests in parallel after migration T004
- After Foundational: US3 bot work can run parallel to US1 web CRUD
- US4 and US5 can run in parallel after US2
- T046/T047/T049 polish tasks in parallel

---

## Parallel Example: User Story 1

```bash
# After Foundational, launch API routes in parallel:
Task: "Implement GET/POST in web/src/app/api/wish-list/route.ts"
Task: "Implement PATCH/DELETE in web/src/app/api/wish-list/[id]/route.ts"
Task: "Implement POST reorder in web/src/app/api/wish-list/reorder/route.ts"

# UI pieces in parallel:
Task: "Create WishListItemForm.tsx"
Task: "Create WishListActiveList.tsx"
Task: "Add navWishList to SideDrawer.tsx"
```

## Parallel Example: User Story 3

```bash
# Tests first in parallel:
Task: "tests/test_wish_list_intent.py"
Task: "tests/test_wish_list_budget.py"
Task: "tests/test_wish_list_confirm.py"

# Then implementation (intent + budget helper can proceed in parallel):
Task: "Extend services/intent.py"
Task: "Implement services/wish_list_budget.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Web CRUD + reorder + sort independently
5. Demo `/wish-list` before execute/bot work

### Incremental Delivery

1. Setup + Foundational → schema and helpers ready
2. US1 → maintain list (MVP)
3. US2 → execute to expense
4. US3 → bot add + budget impact (can overlap with US1 after T009)
5. US4 → executed filter
6. US5 → expense card tag
7. Polish → pytest/lint/quickstart

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Developer A: US1 → US2 → US4/US5
3. Developer B: US3 bot path (after T009)
4. Integrate and run Phase 8 together

---

## Notes

- [P] tasks = different files, no dependencies on incomplete sibling tasks
- [Story] label maps task to US1–US5 for traceability
- Execute is **web-only**; bot is **add yes/no only**
- Do not overload `category_source` for wish origin — use `wish_list_item_id`
- Commit after each task or logical group
- Avoid: vague tasks, same-file conflicts, skipping Foundational migration
