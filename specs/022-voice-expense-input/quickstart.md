# Quickstart: Voice Expense Input

**Feature**: 022-voice-expense-input

## Prerequisites

- Bot baseline: text expense logging, wish list, reply-edit, usage limits  
- `GEMINI_API_KEY` for transcription + expense parse  
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` to persist expenses / inbound rows / metering  
- Apply inbound `audio` message_type migration (see [contracts/supabase-schema-delta.md](./contracts/supabase-schema-delta.md))

## Apply migration

```bash
# From repo root — after adding supabase/migrations/*_inbound_audio_message_type.sql
supabase db push
# Or run the SQL in the Supabase SQL editor
```

## Local harness — expense by voice

```bash
# Short clip that says e.g. "Lunch twelve hundred yen" (m4a/mp4 preferred)
python3 local_run.py --audio path/to/expense.m4a
# Expect: same style expense confirmation as text
```

Group ledger:

```bash
python3 local_run.py --group-id <group_id> --audio path/to/expense.m4a
```

Wish intent by voice (spoken “I want to buy…” / “買いたい…”):

```bash
python3 local_run.py --audio path/to/wish.m4a
# Expect: wish propose + confirm, no expense until yes via text reply
python3 local_run.py --reply-to <bot_message_id> --text "yes"
```

Reply-edit remains text:

```bash
python3 local_run.py --reply-to <bot_message_id> --text "3800円"
```

## Abuse limit checks (manual / harness)

Prepare fixtures:

- `too_long.m4a` — duration &gt; 60s (or harness flag / mocked duration)  
- `too_big.m4a` — file size &gt; 5 MiB  
- `silent.m4a` — near-silent / empty speech  

```bash
python3 local_run.py --audio path/to/too_long.m4a
# Expect: too-long reply naming 60 seconds; no expense

python3 local_run.py --audio path/to/too_big.m4a
# Expect: too-large reply naming 5 MB; no expense

python3 local_run.py --audio path/to/silent.m4a
# Expect: unusable/retry guidance; no expense
```

## Automated tests

```bash
python3 -m pytest -q tests/test_audio_limits.py tests/test_process_audio_message.py
python3 -m pytest -q tests/functional/bot/test_voice_expense_flow.py
python3 -m pytest -q   # full bot suite including functional
```

## Live LINE smoke (optional)

1. Add bot as friend / open group with bot.  
2. Hold-to-talk: “Lunch 1200 yen” → confirmation.  
3. Send a deliberately long voice (&gt;60s) → rejection naming the limit.  
4. Reply to confirmation with a corrected amount in text.

## Architecture note

When implementing, update `docs/ARCHITECTURE.md` so expense capture lists **voice/audio** beside text and image.
