---
description: "Task list for Monthly Budget Manager feature implementation"
---

# Tasks: Monthly Budget Manager

**Input**: Design documents from `/specs/012-monthly-budget-manager/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md; features **009**, **010**, and **011** complete

**Tests**: Vitest for `lib/budget/` included per plan.md constitution compliance (cascade + health). SQL fixtures for RLS and bucket assignment in Foundational; manual quickstart checklist in Polish.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module scaffolding, i18n, and test runner paths for budget feature

- [x] T001 Create budget type definitions in `web/src/lib/budget/types.ts` per `specs/012-monthly-budget-manager/data-model.md` (BudgetLevel, BudgetSummary, BudgetRow, HealthResult)
- [x] T002 [P] Add budget i18n key placeholders in `web/src/lib/i18n/messages.ts` (`navBudget`, pace labels, unlimited state, editor labels, validation errors — ja/en/zh)
- [x] T003 [P] Extend `web/vitest.config.ts` include pattern for `web/src/lib/budget/**/*.test.ts` if not already covered

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema migration, summary RPC, shared budget library, and SQL/Vitest tests that MUST complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create Supabase migration `supabase/migrations/20260624120000_monthly_budgets_tenant.sql` per `specs/012-monthly-budget-manager/contracts/supabase-schema-delta.md` (tenant columns, `budget_level`, nullable total row, indexes, backfill from `line_user_id`, RLS policies)
- [x] T005 Implement `resolve_budget_bucket` SQL function in the same migration file (L2 → L1 → total → unbudgeted cascade per research Decision 4)
- [x] T006 Implement `get_budget_summary` RPC in the same migration file returning JSON shape per `specs/012-monthly-budget-manager/contracts/budget-api.md` and `data-model.md`
- [x] T007 Apply migration to Supabase project and verify `monthly_budgets` RLS policies (document confirmation in `specs/012-monthly-budget-manager/quickstart.md`)
- [x] T008 [P] Implement `resolveBudgetBucket` in `web/src/lib/budget/cascade.ts` mirroring SQL cascade rules for L1/L2 expenses
- [x] T009 [P] Implement pace health computation in `web/src/lib/budget/health.ts` (spentPct, timePct, paceRatio, tone, labelKey; day-1 neutral per spec assumptions)
- [x] T010 [P] Implement display helpers in `web/src/lib/budget/format.ts` (yen formatting, percent, remaining/daily allowance strings)
- [x] T011 [P] Implement PUT payload validation in `web/src/lib/budget/validation.ts` (positive amounts, level/category consistency, clear_levels shape)
- [x] T012 [P] Implement server helpers in `web/src/lib/budget/server.ts` (`fetchBudgetSummary` RPC call, tenant param parsing, reuse `can_access_tenant` pattern from `web/src/lib/periodic/tenant-access.ts`)
- [x] T013 [P] Create Vitest matrix in `web/src/lib/budget/cascade.test.ts` for FR-007 scenarios (L2 budget hit, L1 fallback, total-only, unbudgeted, L2 expense with L1-only budget)
- [x] T014 [P] Create Vitest matrix in `web/src/lib/budget/health.test.ts` for on-track, over-pace, day-1 neutral, and over-100% spent cases
- [x] T015 [P] Create RLS verification SQL in `tests/web/monthly_budgets_rls.test.sql` (personal owner access, group member access, cross-tenant denial)

**Checkpoint**: Foundation ready — migration applied, RPC callable, cascade/health unit tests green

---

## Phase 3: User Story 1 - View monthly budget health at a glance (Priority: P1) 🎯 MVP

**Goal**: Signed-in user opens Budget section and sees current-month total spent, limit (if set), progress bar, health indicator, and unlimited state when no limits configured; respects tenant switcher

**Independent Test**: Set ¥100,000 total budget via SQL or API, log ¥70,000 expenses mid-month, open `/budget` — progress bar ~70%, health color reflects overspending vs days elapsed; switch tenant shows isolated data

### Implementation for User Story 1

- [x] T016 [P] [US1] Implement `GET` handler in `web/src/app/api/budgets/route.ts` per `specs/012-monthly-budget-manager/contracts/budget-api.md` (tenant params, `get_budget_summary` RPC, error envelope)
- [x] T017 [P] [US1] Create `web/src/components/budget/BudgetTotalCard.tsx` with limit/spent/remaining, progress bar, health color via `health.ts`, and pace label via `format.ts`
- [x] T018 [US1] Create `web/src/components/budget/BudgetPage.tsx` with `TenantSwitcher`, fetch on tenant/month change, unlimited empty state when `has_any_limit` is false
- [x] T019 [US1] Create `web/src/app/(app)/budget/page.tsx` rendering `BudgetPage` inside existing app shell
- [x] T020 [P] [US1] Add `navBudget` link to `NAV_ITEMS` in `web/src/components/SideDrawer.tsx`
- [x] T021 [US1] Add `/budget` route title branch in `web/src/components/AppShell.tsx`

**Checkpoint**: User Story 1 complete — user can view total budget health for personal and group ledgers

---

## Phase 4: User Story 2 - Set and edit total, L1, and L2 budgets (Priority: P1)

**Goal**: User configures optional limits at total, L1, and/or L2 with child-sum suggestions and buffer override; clearing a limit returns to unlimited

**Independent Test**: Set L2 budgets under 食費, confirm L1 suggests sum, add ¥5,000 buffer at L1, set total with buffer above L1 sum, save and reload — all amounts persist; clear one L2 limit and confirm it returns to unlimited

### Implementation for User Story 2

- [x] T022 [US2] Implement `PUT` handler in `web/src/app/api/budgets/route.ts` (upsert rows, `clear_levels`, current-month-only guard, validation via `validation.ts`, return refreshed GET shape)
- [x] T023 [US2] Create `web/src/components/budget/BudgetEditor.tsx` with total/L1/L2 amount fields, child-sum suggestions (`suggested_from_children`), buffer override, and save/cancel actions
- [x] T024 [US2] Wire edit mode in `web/src/components/budget/BudgetPage.tsx` (open editor from total card, PUT on save, optimistic refresh)
- [x] T025 [US2] Add editor validation errors and i18n strings in `web/src/lib/i18n/messages.ts` (negative amount, missing category, save success/failure)

**Checkpoint**: User Story 2 complete — user can set and edit budgets for current fiscal month

---

## Phase 5: User Story 3 - Expenses automatically count against applicable budgets (Priority: P1)

**Goal**: Expenses from bot, periodic cron, and all ingestion paths appear in budget spent totals via on-read RPC without bot changes; cascade assigns each expense to exactly one bucket

**Independent Test**: Set L2 budget for 外食 only; log L2 and L3-under-外食 expenses via bot; confirm L2 meter increments; log expense in unbudgeted category — no limit meter changes but `unbudgeted_spent` increases

### Implementation for User Story 3

- [x] T026 [US3] Create SQL cascade fixtures in `tests/web/budget_cascade.test.sql` covering FR-007 acceptance scenarios (L2 hit, L1 fallback, total-only, no budget, soft-deleted exclusion)
- [x] T027 [US3] Ensure `get_budget_summary` in `supabase/migrations/20260624120000_monthly_budgets_tenant.sql` uses total spent = all month expenses when total limit set (research Decision 4 display overlay)
- [x] T028 [US3] Verify periodic auto-logged expenses appear in summary (manual step: create due schedule per `specs/011-periodic-expense-scheduler/quickstart.md`, trigger cron, confirm spent in `BudgetPage.tsx`)
- [x] T029 [US3] Verify mid-month first budget includes prior month expenses in same fiscal month per FR-015 (SQL fixture or manual: insert expenses before budget row, confirm spent in GET response)

**Checkpoint**: User Story 3 complete — all expense sources reflected in budget spent without materialized counters

---

## Phase 6: User Story 4 - Category changes recalculate budget impact (Priority: P1)

**Goal**: Expense amount, category, date, or soft-delete changes are reflected on next budget view without stale spent figures

**Independent Test**: Log ¥3,000 under 外食 with L2 budget; reply-edit category to 食料品; refresh budget — 外食 spent decreases, 食料品 increases when budgeted

### Implementation for User Story 4

- [x] T030 [US4] Extend `tests/web/budget_cascade.test.sql` with category-change and amount-edit scenarios (old bucket decreases, new bucket increases, cross-month date change affects both months)
- [x] T031 [US4] Document reply-edit recalc verification in `specs/012-monthly-budget-manager/quickstart.md` section 5 (bot_message_id flow)
- [x] T032 [US4] Confirm soft-deleted expenses excluded in `get_budget_summary` expense filter (`deleted_at IS NULL`) — add assertion to `tests/web/budget_cascade.test.sql`

**Checkpoint**: User Story 4 complete — expense edits automatically correct budget meters on next load

---

## Phase 7: User Story 5 - Drill down into L1 and L2 budget breakdown (Priority: P2)

**Goal**: User expands budget view to see per-L1 and per-L2 progress bars, health colors, spent/remaining, and inline edit entry points

**Independent Test**: Set total + two L1 + one L2 budget; expand tree — three independent progress bars with correct health colors; L1 without explicit limit shows aggregate spent only

### Implementation for User Story 5

- [x] T033 [P] [US5] Create `web/src/components/budget/BudgetRow.tsx` with per-level progress bar, health tone, spent/limit/remaining, and edit button
- [x] T034 [US5] Create `web/src/components/budget/BudgetCategoryTree.tsx` with expandable L1 rows, nested L2 children, and `has_limit` vs aggregate-only display per spec User Story 5 scenario 2
- [x] T035 [US5] Integrate `BudgetCategoryTree` into `web/src/components/budget/BudgetPage.tsx` below `BudgetTotalCard` with inline edit opening `BudgetEditor` for selected row
- [x] T036 [P] [US5] Create `web/src/components/budget/BudgetEmptyState.tsx` with first-visit onboarding copy and link to start editing

**Checkpoint**: User Story 5 complete — full L1/L2 breakdown visible and editable

---

## Phase 8: User Story 6 - Quick budget setup helpers (Priority: P3)

**Goal**: User can copy prior month budgets or apply 3-month average spending suggestions per category

**Independent Test**: With budgets last month, tap Copy from last month — amounts pre-filled; with 3 months history, suggest on L2 row shows rounded average

### Implementation for User Story 6

- [x] T037 [P] [US6] Implement `POST` handler in `web/src/app/api/budgets/copy-from-previous/route.ts` per `specs/012-monthly-budget-manager/contracts/budget-api.md`
- [x] T038 [P] [US6] Implement `GET` handler in `web/src/app/api/budgets/suggestions/route.ts` calling `monthly_expense_total` for prior 3 months per category
- [x] T039 [US6] Add "Copy from last month" action in `web/src/components/budget/BudgetPage.tsx` (draft pre-fill into `BudgetEditor`, user confirms save)
- [x] T040 [US6] Add per-row "Suggest from history" action in `web/src/components/budget/BudgetEditor.tsx` calling suggestions API; disable when `months_sampled` is 0

**Checkpoint**: User Story 6 complete — copy and suggest shortcuts available

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Usability enhancements, unbudgeted callout, read-only prior month view, and end-to-end validation

- [x] T041 [P] Add unbudgeted spending callout in `web/src/components/budget/BudgetPage.tsx` when `unbudgeted_spent` > 0 per spec usability enhancements
- [x] T042 [P] Add over-budget overrun display (e.g. "¥X over budget") in `web/src/components/budget/BudgetRow.tsx` and `BudgetTotalCard.tsx` when spent > limit
- [x] T043 [P] Add read-only prior-month navigator in `web/src/components/budget/BudgetPage.tsx` (GET with `budget_month` param; editing disabled for non-current months)
- [x] T044 [P] Filter orphan budget rows (deleted category) in `web/src/lib/budget/server.ts` response mapping with UI warning string in i18n
- [ ] T045 Run full manual checklist in `specs/012-monthly-budget-manager/quickstart.md` (personal, group, periodic, reply-edit)
- [x] T046 [P] Run `npm test -- --run src/lib/budget` in `web/` and fix any regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Stories (Phases 3–8)**: All depend on Foundational completion
- **Polish (Phase 9)**: Depends on desired user stories (minimum US1–US4 for P1 scope)

### User Story Dependencies

| Story | Priority | Depends on | Notes |
| ----- | -------- | ---------- | ----- |
| US1 View health | P1 | Foundational | MVP — read-only UI + GET API |
| US2 Set/edit | P1 | US1 page shell | PUT extends same route file |
| US3 Auto counting | P1 | Foundational RPC | Verified via SQL + manual; no bot changes |
| US4 Category recalc | P1 | US3 cascade | On-read; verification tasks only |
| US5 Drill down | P2 | US1, US2 | Tree UI on existing page |
| US6 Quick helpers | P3 | US2 editor | Copy/suggest APIs + buttons |

### Within Each User Story

- Foundational RPC before GET/PUT handlers
- API handlers before UI components that call them
- `BudgetPage` shell before tree/editor integrations

### Parallel Opportunities

- **Phase 1**: T002, T003 in parallel after T001
- **Phase 2**: T008–T015 all parallel after T004–T006 migration file written (T007 apply is sequential after T004–T006)
- **US1**: T016, T017, T020 in parallel; then T018–T019
- **US5**: T033, T036 in parallel; then T034–T035
- **US6**: T037, T038 in parallel; then T039–T040
- **Polish**: T041–T044, T046 in parallel

---

## Parallel Example: User Story 1

```bash
# After Foundational checkpoint, launch in parallel:
Task T016: GET handler in web/src/app/api/budgets/route.ts
Task T017: BudgetTotalCard.tsx
Task T020: SideDrawer navBudget link

# Then sequential:
Task T018: BudgetPage.tsx (depends on T016, T017)
Task T019: budget/page.tsx
Task T021: AppShell title
```

---

## Parallel Example: Foundational

```bash
# After migration file T004–T006 drafted:
Task T008: cascade.ts
Task T009: health.ts
Task T010: format.ts
Task T011: validation.ts
Task T013: cascade.test.ts
Task T014: health.test.ts
Task T015: monthly_budgets_rls.test.sql

# Then apply:
Task T007: supabase db push
Task T012: server.ts (may integrate after T007)
```

---

## Implementation Strategy

### MVP First (User Stories 1–2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: US1 — view budget health
4. Complete Phase 4: US2 — set/edit budgets
5. **STOP and VALIDATE**: User can set a total budget and see progress update after bot-logged expenses

### P1 Scope (add before release)

6. Phase 5: US3 — verify auto counting (SQL + manual)
7. Phase 6: US4 — verify reply-edit recalc

### Incremental Delivery

8. Phase 7: US5 — L1/L2 drill-down UI
9. Phase 8: US6 — copy/suggest helpers
10. Phase 9: Polish — unbudgeted callout, prior month view, quickstart validation

### Suggested MVP Scope

**Minimum shippable**: Phases 1–4 (Setup + Foundational + US1 + US2) — user can set budgets and see health at total level.

**P1 complete**: Add Phases 5–6 (US3 + US4 verification).

---

## Notes

- Budget spent is **computed on read** — no expense triggers or bot changes required for US3/US4
- Total progress bar uses **all month expenses**; L1/L2 meters use **cascade-assigned** amounts only (research Decision 4)
- Reuse tenant access patterns from `web/src/lib/periodic/tenant-access.ts` where possible
- Commit after each phase checkpoint; run Vitest before merging Foundational phase
