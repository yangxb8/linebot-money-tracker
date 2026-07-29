# Quickstart: Automated Functional Testing

**Feature**: 021-automated-functional-tests

## Prerequisites

- Python 3.13+ with `pip install -r requirements.txt`
- Node.js for `web/` (`npm ci`)
- No real `GEMINI_API_KEY` / LINE / Supabase production secrets required for the PR-lane suites
- Playwright browsers (after `cd web && npx playwright install`)

## Bot functional suite

```bash
# From repo root — mock env (CI-equivalent)
export LINE_CHANNEL_SECRET=test_secret
export LINE_CHANNEL_ACCESS_TOKEN=test_token
export GEMINI_API_KEY=test_gemini_key

python3 -m pytest -q tests/functional/bot
# Or full suite (unit + functional):
python3 -m pytest -q
```

Expect: signature rejection, text expense confirm, reply-edit, wish accept/decline — all green without network calls to LINE/Gemini.

## Web API functional + unit tests

```bash
cd web
npm ci
# Stub publics if your shell has none (middleware/client imports):
export NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
export NEXT_PUBLIC_SUPABASE_ANON_KEY=test-anon-key

npm run lint
npm test
```

Functional files cover mocked auth + route handlers for expenses, wish list, settings, budgets, categories, and 401.

## Browser smoke

```bash
cd web
npx playwright install   # once per machine
npx playwright test
```

Expect: unauthenticated protected URL → `/login`; mocked signed-in session → dashboard (or chosen page) loads without bounce.

## CI

Push a PR; GitHub Actions should run bot pytest, web lint/test, and Playwright smoke. A failing assertion fails the check. There is **no** check that forces every PR to touch test files.

## Expanding tests on future features (required process)

When adding user-facing behavior:

1. Add or update scenarios in the appropriate suite (`tests/functional/bot/`, web `*.functional.test.ts`, or unit tests for pure logic).
2. Include explicit test-expansion tasks in `/speckit-plan` / `/speckit-tasks` artifacts.
3. Keep PR-lane mocks — do not point functional tests at the live household project.
4. See `AGENTS.md` → **Test suite expansion**.

## Out of scope here

- Live Gemini `local_run.py` packs (manual / future deep lane)
- Receipt/image bot functional scenarios
- Periodic-expense web functional scenarios
- Nightly bot→web cross-surface job
