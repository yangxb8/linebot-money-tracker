# Quickstart: Simplify LINE expense confirmation replies

This quickstart covers how to validate the simplified confirmation reply behavior locally (tests + basic dev flows).

## Prerequisites

- Python dependencies installed (repo root)
- Web dependencies installed (`web/`) if validating the settings UI
- For running the bot harness end-to-end, a real `GEMINI_API_KEY` is required (tests do not require it)

## Bot: run tests

From repo root:

- `python3 -m pytest -q`

Expected: tests pass without needing LINE/Supabase/Gemini credentials.

## Bot: local harness (requires `GEMINI_API_KEY`)

1. Run a simple single-item expense:
   - `python3 local_run.py --text "Lunch 1200 yen"`
2. Confirm the reply is compact and does not include a long instruction block.

## Reply-edit confirmation flow (YES)

1. Log an expense and note `bot_message_id` in output.
2. Reply with a non-exact category phrase:
   - `python3 local_run.py --reply-to <bot_message_id> --text "groceri"` (typo / partial)
3. Confirm the bot replies with a guessed category path and requests `YES`.
4. Confirm by replying:
   - `python3 local_run.py --reply-to <bot_message_id> --text "YES"`

## Web: validate per-item detail setting (optional)

From `web/`:

- Create `web/.env.local` based on `web/.env.example`
- Ensure `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set, otherwise middleware will error on all pages
- `npm install`
- `npm run dev`

In the Settings area, toggle the confirmation display preference (show per-item details). Then re-run the harness multi-item flow and confirm the reply includes per-item lines when enabled.
