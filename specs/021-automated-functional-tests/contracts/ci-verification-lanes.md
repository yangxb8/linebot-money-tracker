# Contract: CI Verification Lanes

**Feature**: 021-automated-functional-tests  
**Workflow**: `.github/workflows/ci.yml`

## Lane: `pr_fast` (required)

**Triggers**: `push` to `main`/`master`, all `pull_request`s.

### Job: `bot`

| Step | Contract |
| ---- | -------- |
| Setup | Python 3.13; `pip install -r requirements.txt` |
| Env | `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `GEMINI_API_KEY` mock values only |
| Run | `python -m pytest -q` (includes `tests/` + `tests/functional/bot/`) |
| Fail | Non-zero exit fails the workflow (hard gate) |

### Job: `web-unit`

| Step | Contract |
| ---- | -------- |
| Setup | Node LTS matching project; `npm ci` in `web/` |
| Env | Stub `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` if lint/tests import clients |
| Run | `npm run lint` and `npm test` (unit + functional Vitest) |
| Fail | Non-zero exit fails the workflow |

### Job: `web-e2e-smoke`

| Step | Contract |
| ---- | -------- |
| Setup | Same Node install; `npx playwright install --with-deps` (or cached browsers) |
| Run | Playwright project limited to `web/e2e` smoke specs |
| Fail | Non-zero exit fails the workflow |
| Secrets | No production Supabase/LINE/Gemini secrets |

### Explicit non-requirements

- No job that fails solely because the PR diff omits test file paths.
- No dependency on production household Supabase project.
- SQL RLS files under `tests/web/*.sql` remain optional/manual unless already wired; do not block this feature’s PR lane on remote DB.

## Lane: `deep_scheduled` (out of v1 delivery)

Documented for later:

- Schedule trigger (e.g. nightly)
- Isolated remote test tenant
- Optional real Gemini + bot→web observability
- Never a required status check for merge while FR-012 remains optional

## Policy coupling

| Mechanism | Behavior |
| --------- | -------- |
| Soft | `AGENTS.md` + constitution: features incomplete without test expansion |
| Hard | Any red `pr_fast` job blocks green CI |

## Success mapping

- SC-003 → all three `pr_fast` jobs run on every PR
- SC-005 → mocked/stub envs only in `pr_fast`
- FR-016 → no test-diff-required check
