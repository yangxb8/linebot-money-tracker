# Implementation Plan: Voice Expense Input

**Branch**: `cursor/voice-expense-input-56c0` | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/022-voice-expense-input/spec.md`

## Summary

Accept LINE **voice/audio** messages as expense input. Enforce abuse limits (**60 seconds** duration, **5 MB** size) before speech understanding. Transcribe audio with Gemini multimodal (general model chain, not receipt), then **reuse the existing text expense / wish-list pipeline** so confirmation, reply-edit, persona/i18n, tenant rules, and metering stay consistent. Extend inbound retry schema for `audio`, add `local_run.py --audio`, and expand `tests/functional/bot/` per FR-011. Update `docs/ARCHITECTURE.md` when implementing (new primary inbound surface).

## Technical Context

**Language/Version**: Python 3.11+ (bot); SQL (Supabase Postgres migration for inbound `message_type`); no web UI changes

**Primary Dependencies**: FastAPI webhook (`main.py`), `line-bot-sdk` (AudioMessage + `AsyncMessagingApiBlob.get_message_content`), Gemini client (`services/gemini_client.py` / `metered_gemini.py`), existing `process_text_message` / intent / wish-list paths, `confirmation_i18n` + persona stack, usage limiter (`services/usage_limiter.py` / `usage_config.py`)

**Storage**: Supabase — extend `inbound_messages.message_type` CHECK to include `audio` (and failure kinds for audio fetch); no new expense columns (voice-origin expenses are normal expense rows)

**Testing**: `pytest` unit tests for limits + transcription handoff; `tests/functional/bot/` scenarios (happy path, over-duration, over-size, unusable/non-expense) with mocked Gemini/LINE/Supabase; no live production ledger mutation

**Target Platform**: LINE bot on Cloud Run + local console harness; Supabase household project

**Project Type**: Chat bot extension (monorepo Python bot + shared Supabase); web dashboard unchanged in v1

**Performance Goals**: Typical &lt;15s clip → confirmation within **10s** user-perceived wait (SC-003); reject over-limit audio without Gemini call

**Constraints**:
- Max duration **60s**, max size **5 MB** (FR-004/FR-005); reject before full speech understanding
- Reuse text confirmation / reply-edit (text-only edits in v1); no parallel voice confirm UX
- Meter voice as **general/assist** usage (not `receipt_analysis`)
- Idempotent inbound handling same as text/image
- All user-facing replies via i18n/persona stack
- Expand functional suite in the same PR as implementation (constitution + AGENTS.md)

**Scale/Scope**: Household LINE users; short expense utterances; one audio message → one transcription → existing multi-item text semantics

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | New thin audio extract/limit/transcribe modules; hand off to existing text handler; no duplicated expense persist path |
| Test-First Delivery | Unit + functional bot tests for happy path and abuse limits before/with webhook wiring (FR-011) |
| User Experience Consistency | Same confirmation shape as text; clear over-limit / unusable replies via i18n keys |
| Performance & Reliability | Bound size/duration; fail closed on over-limit without LLM; graceful undecodable/silent handling |
| Observability & Feedback | Log audio accept/reject reasons, duration/size, transcription empty vs expense path |

**Gate**: PASS (pre- and post-design)

## Project Structure

### Documentation (this feature)

```text
specs/022-voice-expense-input/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── voice-bot.md
│   ├── audio-limits.md
│   └── supabase-schema-delta.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
# Schema
supabase/migrations/YYYYMMDDHHMMSS_inbound_audio_message_type.sql

# Bot — inbound + limits
services/line_event.py              # extract_audio_message_id (+ duration ms)
services/audio_limits.py            # size/duration constants + validators
services/usage_config.py            # USAGE_MAX_AUDIO_BYTES (default 5 MiB)
services/usage_limiter.py           # check_payload_audio; prepare_inbound_usage audio path
services/inbound_message_repository.py  # save_inbound_audio_message; message_type=audio
services/message_retry.py           # retry audio fetch + process_audio_message

# Bot — speech + handler
services/gemini_client.py           # generate_text/json with audio Part
services/metered_gemini.py          # meter audio calls as general/assist
services/ai_assist.py               # transcribe_audio_message (or equivalent)
services/message_handler.py         # process_audio_message → limits → transcribe → text path
services/confirmation_i18n.py       # over_limit / unusable audio strings (JA/EN/ZH)
services/persona_i18n.py            # persona variants for new keys if required
main.py                             # audio branch; generalize content fetch
local_run.py                        # --audio path/to/clip.m4a

# Tests
tests/test_audio_limits.py
tests/test_process_audio_message.py   # or similar unit coverage
tests/functional/bot/helpers/webhook_events.py  # audio_message_event
tests/functional/bot/test_voice_expense_flow.py

# Docs (implement PR)
docs/ARCHITECTURE.md                # expense capture includes voice/audio
```

**Structure Decision**: Extend the existing Python bot at repo root + Supabase migrations. No new top-level package; no web changes in v1.

## Implementation Approach

1. **Limits module + usage config**: Centralize `MAX_AUDIO_DURATION_SECONDS=60`, `MAX_AUDIO_BYTES=5*1024*1024` (env-overridable size like images); validate duration from LINE webhook ms and size from downloaded bytes (reject before Gemini).
2. **LINE extract + webhook branch**: `extract_audio_message` (`type == audio`, message id, optional `duration`); fetch via existing blob API; save inbound audio row; reply with localized over-limit messages when capped.
3. **Transcribe then text**: Gemini multimodal audio → plain transcript string; on empty/unusable → retry guidance; else call existing `process_text_message` (expense + wish-list parity).
4. **Retry + schema**: Migration allows `message_type='audio'`; retry re-fetches content like image.
5. **Harness + tests**: `local_run.py --audio`; functional scenarios for confirm, over-duration, over-size, unusable/non-expense (mocked).
6. **Architecture doc**: Document voice as a primary expense-capture input alongside text/image.

## Complexity Tracking

> No constitution violations requiring justification.
