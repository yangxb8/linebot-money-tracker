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

### Spec Kit (`/speckit-*` commands)
- This project was initialized with Spec Kit `0.8.18` using PowerShell scripts (`.specify/init-options.json` → `"script": "ps"`). The `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, etc. skills invoke `.specify/scripts/powershell/*.ps1`, so **PowerShell Core (`pwsh`) must be present** on this Linux box — the update script installs it (the `.ps1` scripts are cross-platform and run fine under `pwsh`).
- The `specify` CLI is installed via `uv` (`uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`); both land in `~/.local/bin` (already on PATH via `~/.bashrc`). Verify with `specify check`.
- Sanity-check the command path without a slash command: `pwsh .specify/scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly` from the repo root. Downstream commands resolve the active feature from `.specify/feature.json`, not the git branch name.
