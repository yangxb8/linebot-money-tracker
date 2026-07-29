---
description: "Task list for Automated Functional Testing feature implementation"
---

# Tasks: Automated Functional Testing

**Input**: Design documents from `/specs/021-automated-functional-tests/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: This feature *is* the functional test suite. Story phases deliver executable bot/web/CI scenarios per contracts (not optional). No new production schema.

**Organization**: Tasks grouped by user story (US1 bot → US2 web → US4 policy → US3 CI → US5 deferred). Setup/foundation shared helpers first.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Bot functional: `tests/functional/bot/`
- Web functional: `web/src/**/*.functional.test.ts`, `web/src/lib/test-support/`
- Browser smoke: `web/e2e/`, `web/playwright.config.ts`
- CI: `.github/workflows/ci.yml`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold directories, markers, and dependencies without scenarios yet

- [x] T001 Create `tests/functional/bot/helpers/` package with empty `__init__.py` files under `tests/functional/bot/`
- [x] T002 [P] Add `pytest.ini` at repo root registering marker `functional` (and `asyncio_mode` if needed for consistency)
- [x] T003 [P] Add `@playwright/test` as a direct `devDependency` in `web/package.json` and refresh `web/package-lock.json`
- [x] T004 [P] Extend `web/vitest.config.ts` `include` to pick up `src/**/*.functional.test.ts` (keep existing `*.test.ts`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared mocks/helpers that US1–US3 scenarios depend on

**⚠️ CRITICAL**: Complete before story scenario files (helpers may be refined per story, but skeletons must exist)

- [x] T005 Implement LINE HMAC helper `sign_body(body: bytes, secret: str) -> str` in `tests/functional/bot/helpers/line_signature.py`
- [x] T006 [P] Implement webhook JSON builders (text message, reply-to message) in `tests/functional/bot/helpers/webhook_events.py`
- [x] T007 Create `tests/functional/bot/conftest.py` with env setdefaults (`LINE_CHANNEL_SECRET=test_secret`, token, `GEMINI_API_KEY`), FastAPI `TestClient` fixture for `main.app`, and shared `reply_message` AsyncMock patch fixture
- [x] T008 [P] Create mocked Supabase/auth helpers in `web/src/lib/test-support/mock-supabase.ts` (fake `getUser` user|null + chainable in-memory stubs usable from functional tests)
- [x] T009 [P] Create Playwright config `web/playwright.config.ts` with `testDir: e2e`, stub `NEXT_PUBLIC_SUPABASE_*` env, and `webServer` command for `npm run dev` or `npm run start` as appropriate for smoke

**Checkpoint**: Foundation ready — bot helpers + web mock/support + Playwright config exist

---

## Phase 3: User Story 1 — Catch bot regressions before merge (Priority: P1) 🎯 MVP

**Goal**: Automated bot functional suite covering webhook signature rejection, text expense confirm, reply-edit, wish accept/decline — all mocked, no live LINE/Gemini

**Independent Test**: `python3 -m pytest -q tests/functional/bot` with mock env passes; covers contracts in `contracts/bot-functional-suite.md`

### Implementation for User Story 1

- [x] T010 [US1] Implement `bot.webhook.unsigned` in `tests/functional/bot/test_webhook_signature.py` (missing/invalid `X-Line-Signature` → HTTP 400; `reply_message` not called; do not patch `parser.parse`)
- [x] T011 [P] [US1] Implement valid-signature smoke companion in `tests/functional/bot/test_webhook_signature.py` (correct HMAC allows parse path; may still mock handler downstream)
- [x] T012 [US1] Implement `bot.expense.text_confirm` in `tests/functional/bot/test_expense_text_flow.py` (signed text webhook → confirmation-style reply once; assert expense insert and/or pending confirmation mocks)
- [x] T013 [US1] Implement `bot.expense.reply_edit` in `tests/functional/bot/test_reply_edit_flow.py` (prior pending/confirmation via mocks; reply-to with new amount → mutation + reply reflects change)
- [x] T014 [P] [US1] Implement `bot.wish.accept` in `tests/functional/bot/test_wish_list_flow.py` (wish propose + yes → wish insert called; expense insert not called)
- [x] T015 [P] [US1] Implement `bot.wish.decline` in `tests/functional/bot/test_wish_list_flow.py` (wish propose + no → neither wish nor expense insert)
- [x] T016 [US1] Ensure image/receipt scenarios are absent from `tests/functional/bot/` (document deferral comment in `tests/functional/bot/conftest.py` or module docstring per FR-017)

**Checkpoint**: US1 MVP — four journeys + signature green under `tests/functional/bot/`

---

## Phase 4: User Story 2 — Catch web dashboard regressions before merge (Priority: P1)

**Goal**: Mocked web API/route functional tests for expenses, wish list, settings, budgets, categories + minimal Playwright auth gate and signed-in smoke

**Independent Test**: `cd web && npm test` runs functional Vitest green; `cd web && npx playwright test` runs two smokes green without live Supabase/LINE

### Implementation for User Story 2

- [x] T017 [P] [US2] Add `web.api.unauthorized` functional test in `web/src/app/api/expenses/expenses.functional.test.ts` (or colocated path) — `getUser` null → 401 from expenses route
- [x] T018 [P] [US2] Add `web.api.expenses_overview` in `web/src/app/api/expenses/expenses.functional.test.ts` — mocked user + list/empty 200
- [x] T019 [P] [US2] Add `web.api.wish_list_mutate` in `web/src/app/api/wish-list/wish-list.functional.test.ts` — create then read reflects item
- [x] T020 [P] [US2] Add `web.api.settings_bot_behavior` in `web/src/app/api/settings/settings.functional.test.ts` — save then reload bot-behavior fields
- [x] T021 [P] [US2] Add `web.api.budgets` in `web/src/app/api/budgets/budgets.functional.test.ts` — read/update with expected state
- [x] T022 [P] [US2] Add `web.api.categories` in `web/src/app/api/categories/categories.functional.test.ts` — create/update then read
- [x] T023 [US2] Implement Playwright `web.browser.auth_gate` in `web/e2e/auth-gate.spec.ts` (open `/dashboard` or `/wish-list` without session → `/login`; no private ledger content)
- [x] T024 [US2] Implement Playwright `web.browser.signed_in_smoke` in `web/e2e/signed-in-smoke.spec.ts` (mock signed-in `getUser`/session; open `/dashboard`; no auth bounce)
- [x] T025 [US2] Confirm periodic-expense routes are not covered in v1 functional files (brief note in `web/src/lib/test-support/mock-supabase.ts` or functional test README comment per FR-015)

**Checkpoint**: US2 — API functional set + two browser smokes pass locally

---

## Phase 5: User Story 4 — Future features must grow the suite (Priority: P1)

**Goal**: Soft policy remains authoritative; Spec Kit / agent docs make test-expansion explicit for future work

**Independent Test**: `AGENTS.md` contains Test suite expansion; constitution Test-First requires suite growth; tasks template or feature quickstart instructs `/speckit-tasks` to include expansion tasks

### Implementation for User Story 4

- [x] T026 [P] [US4] Verify and tighten `AGENTS.md` “Test suite expansion” section against FR-009/FR-016 (soft expansion; hard fail only on red suites; point to `specs/021-automated-functional-tests/quickstart.md`)
- [x] T027 [P] [US4] Verify `.specify/memory/constitution.md` Test-First Delivery (0.1.1+) still requires bot+web functional coverage and suite expansion
- [x] T028 [US4] Add a short “Test expansion” note to `.specify/templates/tasks-template.md` Organization/Notes so future `/speckit-tasks` runs include suite-expansion tasks for user-facing features
- [x] T029 [P] [US4] Ensure `.cursor/rules/specify-rules.mdc` references 021 plan/quickstart and the expansion rule (already planned — confirm no drift)

**Checkpoint**: Policy artifacts consistent; no CI test-diff gate added

---

## Phase 6: User Story 3 — Continuous checks on every change review (Priority: P2)

**Goal**: GitHub Actions PR lane runs bot pytest, web lint/unit/functional, and Playwright smoke with mock/stub env only

**Independent Test**: Push/PR triggers green `bot`, `web-unit`, `web-e2e-smoke` jobs without production secrets; deliberate failing assertion fails the workflow

### Implementation for User Story 3

- [x] T030 [US3] Split/rename `.github/workflows/ci.yml` job to `bot` running `python -m pytest -q` with mock LINE/Gemini env (preserve existing behavior; ensure `tests/functional/bot` is collected)
- [x] T031 [P] [US3] Add `web-unit` job to `.github/workflows/ci.yml` (`npm ci`, stub `NEXT_PUBLIC_SUPABASE_*`, `npm run lint`, `npm test`)
- [x] T032 [P] [US3] Add `web-e2e-smoke` job to `.github/workflows/ci.yml` (Playwright install + `npx playwright test` with stub env; no production secrets)
- [x] T033 [US3] Document in `.github/workflows/ci.yml` (comment) and/or `specs/021-automated-functional-tests/quickstart.md` that there is no mandatory test-diff gate (FR-016)
- [x] T034 [US3] Validate CI contracts against `specs/021-automated-functional-tests/contracts/ci-verification-lanes.md` (job names, fail-on-red, no deep lane)

**Checkpoint**: PR lane matches `pr_fast` contract

---

## Phase 7: User Story 5 — Optional deeper confidence (Priority: P3) — deferred

**Goal**: Record deep-lane non-delivery for v1; no scheduled workflow required

**Independent Test**: No nightly job in CI; quickstart lists deep lane as out of scope

- [x] T035 [US5] Add explicit “Deep lane deferred” subsection to `specs/021-automated-functional-tests/quickstart.md` (isolated tenant + optional real AI / bot→web; not a merge gate)
- [x] T036 [P] [US5] Ensure `.github/workflows/` has no required deep/nightly workflow for this feature in v1

**Checkpoint**: US5 documented as deferred; PR lane unaffected

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validate quickstart end-to-end and keep docs aligned

- [x] T037 [P] Run and fix `python3 -m pytest -q` (full unit + functional) until green locally
- [x] T038 [P] Run and fix `cd web && npm run lint && npm test` until green
- [x] T039 [P] Run and fix `cd web && npx playwright test` until green
- [x] T040 Align `specs/021-automated-functional-tests/quickstart.md` commands with final scripts/paths
- [x] T041 [P] Spot-check scenario ids in test names/docstrings against `specs/021-automated-functional-tests/data-model.md` catalog
- [x] T042 Confirm no functional test targets production household Supabase project (FR-008/SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS US1–US3 scenario work (US4 policy can start after Setup)
- **US1 (Phase 3)**: Depends on Phase 2 bot helpers (T005–T007)
- **US2 (Phase 4)**: Depends on Phase 2 web helpers (T008–T009); can parallel US1 after foundation
- **US4 (Phase 5)**: Depends on Setup only; can parallel US1/US2
- **US3 (Phase 6)**: Depends on US1 + US2 suites existing (otherwise CI jobs would be empty/failing)
- **US5 (Phase 7)**: Docs-only; anytime after Setup
- **Polish (Phase 8)**: After desired stories complete (recommend after US1–US4 + US3)

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories — **MVP**
- **US2 (P1)**: Independent of US1 after foundation
- **US4 (P1)**: Independent policy docs
- **US3 (P2)**: Needs US1 + US2 artifacts to wire CI meaningfully
- **US5 (P3)**: Deferred documentation only

### Parallel Opportunities

- T002, T003, T004 after T001 directory exists
- T005 || T006; T008 || T009 after Phase 1
- After T007: T010→T013 sequential where shared fixtures evolve; T014 || T015
- T017–T022 mostly parallel (different route test files)
- T023 then T024 (shared Playwright auth mocking patterns)
- T026 || T027 || T029; T031 || T032 after T030 skeleton

---

## Parallel Example: User Story 1

```bash
# After conftest + helpers:
Task: "T014 wish.accept in tests/functional/bot/test_wish_list_flow.py"
Task: "T015 wish.decline in tests/functional/bot/test_wish_list_flow.py"
# Signature + expense flows can proceed on another agent once T007 exists:
Task: "T010 unsigned webhook in tests/functional/bot/test_webhook_signature.py"
```

## Parallel Example: User Story 2

```bash
Task: "T017–T022 API functional tests across web/src/app/api/**/*.functional.test.ts"
# Then browser (shared auth stub):
Task: "T023 auth-gate.spec.ts"
Task: "T024 signed-in-smoke.spec.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational (bot helpers at minimum)
3. Phase 3 US1 bot suite
4. **STOP and VALIDATE**: `python3 -m pytest -q tests/functional/bot`
5. Demo/merge-ready slice even before web/CI

### Incremental Delivery

1. Setup + Foundation
2. US1 bot suite → validate
3. US2 web API + Playwright → validate
4. US4 policy verify (can interleave earlier)
5. US3 CI jobs → validate on PR
6. US5 deferral note + Polish

### Parallel Team Strategy

1. Shared Setup + Foundation
2. Dev A: US1 bot | Dev B: US2 web mocks/API | Dev C: US4 policy
3. Together: US3 CI once suites exist
4. Polish locally then on CI

---

## Notes

- [P] = different files, no incomplete-task dependencies
- Story labels map to spec user stories US1–US5
- Do not add a CI “must touch test files” check
- Do not implement deep/nightly live-tenant jobs in v1
- Prefer stable reply/API assertions over full persona string equality
- Commit after each task or logical group
