# Data Model: Voice Expense Input

**Feature**: 022-voice-expense-input

## Overview

Voice does **not** introduce a new expense entity. Audio is an inbound message modality that produces a transcript, then the existing expense / wish-list / confirmation model applies unchanged.

```text
LINE AudioMessage
    │  duration_ms (optional), message_id
    ▼
inbound_messages (message_type='audio')
    │
    ▼
abuse limits (duration ≤ 60s, size ≤ 5 MB)
    │
    ▼
transcript (ephemeral) ──► process_text_message
                              │
                              ├── expenses (+ confirmations)   [unchanged]
                              ├── wish_list pending_action     [unchanged]
                              └── unsupported / retry guidance
```

## Entity changes

### inbound_messages (existing)

| Field | Change |
| ----- | ------ |
| `message_type` | CHECK extended: `'text' \| 'image' \| 'audio'` |
| `line_message_id` | Unchanged — LINE audio message id for content fetch / idempotency |
| `raw_text` / body | Audio rows typically have null/empty text; transcript is **not** required to be persisted in v1 |
| failure / retry metadata | Support audio content fetch failures (e.g. `audio_fetch_error`) |

No new columns are required for v1 if existing inbound row shape can store audio message ids and types. Optional future: `metadata.duration_ms` / `metadata.byte_length` for observability — nice-to-have, not required by spec.

### expenses / confirmations / wish_list_items

**No schema changes.** Voice-origin expenses are indistinguishable from text-origin expenses of the same content. Reply-edit continues to key off confirmation `bot_message_id`.

## Validation rules (runtime, not DB)

| Rule | Constraint |
| ---- | ---------- |
| Max duration | `duration_ms <= 60_000` when known; reject if greater |
| Max size | `len(audio_bytes) <= 5_242_880` (5 × 1024 × 1024) |
| Accept boundary | Equal to max is allowed; strictly greater rejected |
| Empty transcript | No expense / wish insert; user-facing retry guidance |
| MIME | Expect LINE voice as m4a/mp4 audio; undecodable → unusable path |

## State transitions

```text
[audio received]
    → reject_over_duration | reject_over_size
    → fetch_failed (retryable inbound)
    → transcribed_empty (terminal user guidance)
    → transcribed_text → (existing text pipeline states:
         expense_confirmed | wish_proposed | unsupported | parse_error)
```

## Idempotency

Same LINE `message_id` for audio must not create duplicate expenses — reuse existing inbound / expense idempotency keys used for text and image.
