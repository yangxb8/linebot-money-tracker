# Quickstart: Personal Bot Persona Settings

This quickstart covers how to validate the persona settings feature locally (tests + basic dev flows).

## Prerequisites

- Python dependencies installed (repo root)
- Web dependencies installed (`web/`)
- For running the bot harness end-to-end, a real `GEMINI_API_KEY` is required (tests do not require it)

## Bot: run tests

From repo root:

- `python3 -m pytest -q`

Expected: tests pass without needing LINE/Supabase/Gemini credentials.

## Web: run dev server (settings UI)

From `web/`:

- Create `web/.env.local` based on `web/.env.example`
- Ensure `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set, otherwise middleware will error on all pages
- `npm install`
- `npm run dev`

Navigate to the Settings area and verify the “LINE bot behavior” section displays and persists persona fields via `/api/settings`.

## End-to-end persona behavior (requires keys)

To confirm the bot replies reflect a configured persona:

1. Use the web settings UI to configure persona for the relevant tenant:
   - Personal chat: `tenant_type=user`, `tenant_id=<your LINE user id>`
   - Group chat: `tenant_type=group`, `tenant_id=<group id>`
2. Run the bot console harness:
   - `python3 local_run.py --text "Lunch 1200 yen"`
3. Confirm the reply uses the configured persona style; reset persona in web settings and confirm replies return to default.
