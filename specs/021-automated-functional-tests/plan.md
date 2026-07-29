# Implementation Plan: Automated Functional Testing

**Branch**: `cursor/automated-functional-tests-a58c` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/021-automated-functional-tests/spec.md`

## Summary

Add a **fast PR verification lane** of automated functional tests for the LINE bot and Next.js web dashboard, fully mocked (no live LINE/Gemini/Supabase). Bot coverage: webhook signature rejection plus text expense confirm, reply-edit, wish accept/decline via HTTP `/callback` and handler boundaries. Web coverage: Vitest API/route functional tests for expenses, wish list, settings, budgets, and categories, plus minimal Playwright browser smoke (auth gate + one signed-in page). Extend GitHub Actions to run bot pytest (including new functional tests), web lint/unit/functional, and Playwright smoke. Keep agent/constitution **soft** policy that future features expand tests; **hard** CI fail only when suites fail. Optional deep/nightly lane is out of v1 delivery.

## Technical Context

**Language/Version**: Python 3.13 (bot/CI); TypeScript/Node (Next.js 15 web)

**Primary Dependencies**: FastAPI + `starlette.testclient`/`httpx` for bot webhook HTTP; existing `unittest.mock` patch style; Vitest + `vi.mock` for web route handlers; Playwright (`@playwright/test`) as new direct web devDependency for smoke only

**Storage**: N/A for PR lane (all auth/data/externals mocked). No new Supabase migrations. Optional deep lane (deferred) would use an isolated remote test tenant later.

**Testing**: `pytest` + `pytest-asyncio` with new `tests/functional/bot/`; Vitest functional files under `web/src/**/*.functional.test.ts` (or `web/tests/functional/`); Playwright under `web/e2e/`; GitHub Actions multi-job CI

**Target Platform**: GitHub Actions Ubuntu runners + local developer machines

**Project Type**: Dual-surface monorepo (Python LINE bot + Next.js dashboard) — test-infrastructure feature

**Performance Goals**: Bot functional suite &lt; 5 minutes; web API functional + browser smoke &lt; 10 minutes (SC-001/SC-002)

**Constraints**:
- PR lane MUST NOT use production household data or production LINE/AI/Supabase credentials (FR-008, FR-018)
- No mandatory “PR must touch test files” gate (FR-016)
- Image/receipt bot journeys and web periodic-expense journeys deferred (FR-017, FR-015)
- Browser automation limited to auth gate + one signed-in page (FR-014)
- Agent policy already in `AGENTS.md` / constitution 0.1.1 — reinforce in Spec Kit task templates / quickstart only as needed

**Scale/Scope**: ~4–6 bot functional scenarios; ~6–8 web API scenarios + 2 browser smokes; CI jobs for python + web; no schema changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Reuse existing handler/webhook mock boundaries and web `require*User` helpers; shared HMAC/fixture helpers under `tests/functional/bot/`; avoid parallel persistence stacks |
| Test-First Delivery | Feature *is* the functional suite; scenarios derived from clarified acceptance criteria before wiring; future features must expand suites (soft policy already documented) |
| User Experience Consistency | Assertions target stable reply/API contracts (structure, status, side-effect calls), not brittle full persona strings |
| Performance & Reliability | Suites bounded by SC time budgets; mocks eliminate external flakiness; few browser paths |
| Observability & Feedback | Clear pytest/vitest/playwright fail output; quickstart documents local commands |

**Gate**: PASS (pre- and post-design)

## Project Structure

### Documentation (this feature)

```text
specs/021-automated-functional-tests/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── bot-functional-suite.md
│   ├── web-functional-suite.md
│   └── ci-verification-lanes.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
# Bot functional suite
tests/functional/
└── bot/
    ├── conftest.py                 # env, TestClient, shared patches
    ├── helpers/
    │   ├── line_signature.py       # HMAC X-Line-Signature for test_secret
    │   └── webhook_events.py       # LINE webhook JSON builders
    ├── test_webhook_signature.py
    ├── test_expense_text_flow.py
    ├── test_reply_edit_flow.py
    └── test_wish_list_flow.py

# Optional marker registration
pytest.ini                          # markers: functional (or pyproject)

# Web API functional tests
web/src/lib/test-support/           # optional shared mock supabase/auth helpers
web/src/**/*.functional.test.ts     # or web/tests/functional/*.test.ts
web/vitest.config.ts                # include functional patterns

# Browser smoke
web/e2e/
├── auth-gate.spec.ts
└── signed-in-smoke.spec.ts
web/playwright.config.ts

# CI
.github/workflows/ci.yml            # jobs: bot-pytest, web-unit, web-e2e-smoke

# Policy (already partially done in specify)
AGENTS.md                           # test-expansion section (verify/complete)
.specify/memory/constitution.md     # 0.1.1 Test-First (already amended)
```

**Structure Decision**: Keep existing flat `tests/test_*.py` unit suite unchanged; add a dedicated `tests/functional/bot/` tree for product-boundary HTTP/handler scenarios. Web unit tests stay under `src/lib/**/*.test.ts`; add functional route tests as `*.functional.test.ts` and Playwright under `web/e2e/`. No new application runtime modules beyond thin test helpers.

## Complexity Tracking

> No constitution violations requiring justification.
