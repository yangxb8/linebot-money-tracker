# AGENTS.md

## Cursor Cloud specific instructions

This repo has two independently runnable components plus a shared Supabase backend:

- **Python LINE bot** (repo root): console harness `local_run.py` and FastAPI webhook `main.py`. Business logic in `services/`.
- **Next.js web dashboard** (`web/`): expense viewing, category/budget/periodic-expense management.
- **Supabase** project `household` (`https://nyuenufldaqsjybjhawl.supabase.co`) — live Postgres with real data; schema in `supabase/migrations/`.

The update script installs both dependency sets (`pip install -r requirements.txt` + `npm install` in `web/`). The notes below are non-obvious gotchas; standard commands live in `README.md`, `web/package.json`, and `specs/*/quickstart.md`.

### Python / interpreter gotchas
- Only `python3` is on PATH (no `python`); the README's `python ...` commands must be run as `python3 ...`.
- pip console scripts (`pytest`, `uvicorn`) install to `~/.local/bin`, which is not on PATH. Invoke them as modules: `python3 -m pytest -q`, `python3 -m uvicorn main:app --reload`.
- Tesseract is NOT installed in this environment. Text expense flows do not need it; only local receipt-image OCR does (set `GOOGLE_VISION_API_KEY` to use the Cloud Vision fallback instead).

### Bot — lint/test/run
- Tests: `python3 -m pytest -q` (uses mock credentials; no Gemini/LINE/Supabase keys required). This is the primary key-free verification of the bot's core pipeline.
- Run: `python3 local_run.py --text "Lunch 1200 yen"`. **Requires a real `GEMINI_API_KEY`** — the harness exits with code 1 if it is unset (there is no offline/mock mode for the running app). Persisting expenses additionally needs `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.

### Web — lint/test/build/run
- From `web/`: `npm run lint`, `npm test` (vitest), `npm run build`, `npm run dev` (Next.js + Turbopack on port 3000).
- `web/.env.local` is gitignored and is NOT created by the update script — recreate it from `web/.env.example` before running the dev server.
- The Next.js middleware calls Supabase on **every** request, so `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` must be set or all pages (including `/login`) error. The anon/publishable keys are public and retrievable from the Supabase project.
- Authenticated dashboard flows additionally require `SUPABASE_SERVICE_ROLE_KEY` (admin client) and a LINE Login channel: `LINE_LOGIN_CHANNEL_ID`, `LINE_LOGIN_CHANNEL_SECRET`, `NEXT_PUBLIC_LINE_LIFF_ID`. Without these, `/login` renders but the LINE sign-in flow cannot complete, and protected pages bounce back to `/login`.

### Test suite expansion (required for every feature)
- Any new user-facing feature is **incomplete** until the automated test suite is expanded to cover that feature’s primary acceptance scenarios. Manual quickstart notes alone are not enough.
- Soft policy: humans/agents/PR review enforce expansion. Hard gate: CI fails when any required suite is red. There is **no** mandatory “PR diff must touch test files” check.
- Prefer the fastest reliable layer: bot/web unit tests for pure logic; `tests/functional/bot/` for chat journeys (mocked Gemini/LINE/Supabase); `*.functional.test.ts` / `web/e2e` for dashboard journeys. Never mutate the live household production ledger in automated tests.
- When running `/speckit-plan` or `/speckit-tasks`, include explicit test-expansion tasks. When implementing, add or update tests in the same PR and keep these green:
  - `python3 -m pytest -q` (includes `tests/functional/bot/`)
  - `cd web && npm test` (unit + functional)
  - `cd web && npx playwright test` (auth gate + signed-in smoke)
- See `specs/021-automated-functional-tests/quickstart.md`. Pure refactors may only require existing suites to stay green; copy/i18n/persona changes still need an assertion on the affected user-visible path.
- v1 functional coverage: bot expense confirm, reply-edit, wish accept/decline; web expenses, wish list, settings, budgets, categories + browser auth gate / signed-in smoke.

### Bot — behavior settings (Settings → LINE bot behavior)
- All user-facing bot text MUST go through the i18n/persona stack (`confirmation_i18n.t()` for templates; `persona_scope(resolve_persona_for_tenant(tenant))` around handlers) so **reply language**, **character/persona preset**, **emoji level**, and **custom style text** from the web app are honored.
- Resolve settings with `resolve_effective_bot_settings(tenant)` / `resolve_tenant_reply_language(tenant, base_language)` / `resolve_persona_for_tenant(tenant)`. In group/room chats, when the shared ledger has no customized bot-behavior fields, fall back to the sender's **personal** tenant settings before defaults or message-language heuristics.
- Do not call `detect_reply_language(user_text)` alone for outbound copy; it is only a fallback input to `resolve_tenant_reply_language`.
- Wish-list budget impact: always show remaining budget when a limit applies (L2 → L1 → total cascade); append a **pace-ahead warning** only when the hypothetical purchase would exceed the daily budget average (`is_ahead_if_purchased`).

### Spec Kit (`/speckit-*` commands)
- This project was initialized with Spec Kit `0.8.18` using PowerShell scripts (`.specify/init-options.json` → `"script": "ps"`). The `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, etc. skills invoke `.specify/scripts/powershell/*.ps1`, so **PowerShell Core (`pwsh`) must be present** on this Linux box — the update script installs it (the `.ps1` scripts are cross-platform and run fine under `pwsh`).
- The `specify` CLI is installed via `uv` (`uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`); both land in `~/.local/bin` (already on PATH via `~/.bashrc`). Verify with `specify check`.
- Sanity-check the command path without a slash command: `pwsh .specify/scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly` from the repo root. Downstream commands resolve the active feature from `.specify/feature.json`, not the git branch name.
