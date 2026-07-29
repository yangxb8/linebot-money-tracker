# Research: Automated Functional Testing

**Feature**: 021-automated-functional-tests  
**Date**: 2026-07-29

## Decision 1: Bot functional tests via FastAPI TestClient on `/callback`

**Decision**: Add HTTP-level tests using Starlette/FastAPI `TestClient` (or `httpx.ASGITransport`) against `main.app` `POST /callback`. Exercise real `WebhookParser` signature validation for unauthorized cases. For happy-path journeys, send correctly signed webhook bodies and mock `line_bot_api.reply_message` plus Gemini/persist boundaries (same seams as `tests/test_message_handler*.py`), without patching `parser.parse` when testing signatures.

**Rationale**: Spec requires product-boundary coverage (inbound → reply). Today `test_line_webhook.py` calls `handle_callback` with `parser.parse` always patched, so signature rejection is untested. HTTP client is the natural CI-facing surface.

**Alternatives considered**:
- Keep only direct `handle_callback` unit tests — rejected; misses signature/HTTP contract.
- Live LINE webhook forwarding — rejected; violates FR-003/FR-008 and is slow/flaky.

---

## Decision 2: Bot v1 scenarios = four text/reply journeys (+ signature)

**Decision**: Implement: (1) invalid/missing signature → 400, no reply; (2) text expense → confirmation reply + persist/pending asserts; (3) reply-edit amount; (4) wish accept; (5) wish decline. Defer image/receipt functional scenarios (FR-017).

**Rationale**: Matches clarification Q4 and SC-006 focus on documented text quickstart flows. Image path already has substantial unit coverage.

**Alternatives considered**:
- Include mocked image expense in v1 — deferred by clarification.
- Drive everything only through `local_run.py` — rejected; harder to assert HTTP signature and unsuitable as pure mock CI without Gemini key.

---

## Decision 3: Web API functional tests as Vitest route-handler calls with `vi.mock`

**Decision**: Call Next.js route `GET`/`POST`/`PATCH` handlers directly with `Request` objects. Mock `@/lib/supabase/server` (or per-domain `require*User` + data functions) so auth and DB are in-memory fakes. Cover expenses list, wish-list create/update+read, settings save/reload, budgets read/update, categories create/update, plus 401 without user.

**Rationale**: Clarification chose API/route checks for core mutations. Middleware does not enforce API auth; `require*User` helpers do — mocking at that boundary matches production behavior without booting Next or remote Supabase (FR-018).

**Alternatives considered**:
- Full `next start` + real HTTP only — heavier and still needs mocks for data.
- MSW against running server — more moving parts for v1; optional later.

---

## Decision 4: Minimal Playwright smoke; not full E2E matrix

**Decision**: Add `@playwright/test` as a direct `web` devDependency. Two specs: unauthenticated visit to a protected app URL → lands on `/login`; mocked signed-in session → one page (e.g. `/dashboard`) loads without auth bounce. Stub browser Supabase/`getUser` (and API routes if needed) so no live credentials.

**Rationale**: Clarification Q1/Q5 — browser only for auth gate + one page; mutations proven via API tests. `AppAuthProvider` performs client redirect; middleware alone does not block `/dashboard`.

**Alternatives considered**:
- Browser-only for all journeys — rejected (flake, slow).
- Skip browser entirely — rejected; auth UX redirect would be untested at UI layer.
- Automate real LINE Login — rejected for PR lane.

---

## Decision 5: CI multi-job PR lane; no test-diff gate; no deep lane in v1

**Decision**: Extend `.github/workflows/ci.yml`:
1. **bot**: install `requirements.txt`, `python -m pytest -q` (picks up `tests/functional/bot/` automatically) with mock LINE/Gemini env.
2. **web-unit**: `npm ci`, `npm run lint`, `npm test` (unit + functional Vitest).
3. **web-e2e**: install Playwright browsers, run `web/e2e` smoke with mock env / stubs.

No job that requires “diff must include tests”. No nightly deep-lane workflow in v1 (FR-012 optional later).

**Rationale**: Clarification Q3/Q5 and FR-007/FR-016/FR-018. Current CI only runs Python pytest — web is unchecked on PRs today.

**Alternatives considered**:
- Single job sequential — slower feedback; prefer parallel jobs.
- Hard “must touch `*test*` files” — rejected by clarification.
- Remote Supabase test project on every PR — rejected by clarification Q5.

---

## Decision 6: Policy artifacts already mostly done; reinforce in quickstart + Spec Kit tasks

**Decision**: Treat `AGENTS.md` test-expansion section and constitution 0.1.1 as the soft enforcement mechanism. Plan/tasks for *this* feature deliver suites; `/speckit-tasks` for future features should include test-expansion tasks (document in quickstart). Do not add a custom GitHub Action for policy linting in v1.

**Rationale**: FR-009/FR-010/FR-016 and clarification Q3.

**Alternatives considered**:
- CODEOWNERS / required checklist bot — out of scope for v1.
- Amend Spec Kit templates globally — optional follow-up; note in tasks if low-cost.

---

## Decision 7: pytest layout under `tests/functional/bot/` without moving legacy tests

**Decision**: Leave existing flat `tests/test_*.py` in place. New functional tests live under `tests/functional/bot/`. Register `@pytest.mark.functional` optionally via `pytest.ini` for filtering; default CI runs the full tree.

**Rationale**: Minimizes churn; discovery works with default pytest recursion.

**Alternatives considered**:
- Move all tests into unit/functional trees — large noisy refactor; defer.
