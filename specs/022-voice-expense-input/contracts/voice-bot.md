# Voice Bot Contract

**Feature**: 022-voice-expense-input  
**Type**: LINE webhook + Python services

## LINE webhook

### Event recognition

| Field | Rule |
| ----- | ---- |
| `events[].type` | `message` |
| `events[].message.type` | `audio` |
| `events[].message.id` | Required — content fetch key |
| `events[].message.duration` | Optional — milliseconds; used for pre-fetch duration limit |

### Extractor

Module: `services/line_event.py`

```text
extract_audio_message(event) -> { message_id: str, duration_ms: int | None } | None
```

Returns `None` unless `message.type == "audio"`.

### Content fetch

Same Messaging API blob endpoint as images:

```text
GET message content by message_id → bytes (typically audio/m4a)
```

Generalize `_fetch_image_bytes` naming to content/blob fetch shared by image and audio.

### Dispatch order (`main.py`)

After existing text / image / reply-edit / retry branches, handle audio before generic unsupported:

1. Extract audio message  
2. If `duration_ms > 60000` → localized too-long reply; **do not** fetch (preferred) or do not call Gemini  
3. Fetch bytes; if `len > 5 MiB` → localized too-large reply; no Gemini  
4. `save_inbound_audio_message` + usage prep  
5. `process_audio_message(...)`  
6. Reply with handler text (confirmation / wish / error)

## Handler

Module: `services/message_handler.py`

```text
process_audio_message(
  audio_bytes: bytes,
  gemini,
  *,
  context,
  duration_ms: int | None = None,
) -> str
```

### Behavior

| Condition | Outcome |
| --------- | ------- |
| Duration over limit | Localized over-duration message; no transcript / expense |
| Size over limit | Localized over-size message; no transcript / expense |
| Transcription empty / unusable | Localized retry/text guidance; no expense |
| Transcript non-empty | Delegate to `process_text_message(transcript, ...)` |

Wish-list and expense confirmations after successful transcription MUST match text-origin contracts.

## Gemini transcription

Module: `services/ai_assist.py` (+ `gemini_client` / `metered_gemini`)

```text
transcribe_audio(audio_bytes, mime_type, gemini) -> str
```

- Prompt: return JSON `{ "transcript": "..." }` and **normalize spoken amounts to Arabic digits + currency** (e.g. `千二百円` / digit-by-digit → `1200円`).  
- Models: general fallback chain.  
- Metering: general/assist — **not** `receipt_analysis`.  
- Empty or whitespace-only transcript → unusable path.

## Inbound persistence

```text
save_inbound_audio_message(line_message_id, tenant..., ...)
message_type = 'audio'
```

Retry: `message_retry` re-fetches audio content and calls `process_audio_message`.

## i18n keys (minimum)

| Key purpose | Must include |
| ----------- | ------------ |
| Audio too long | Max **60 seconds**; suggest shorter clip or text |
| Audio too large | Max **5 MB**; suggest shorter clip or text |
| Unusable audio | Retry or send text |

All keys flow through `confirmation_i18n.t` / persona wrappers.

## Out of contract (v1)

- Voice reply-edit / voice cancel  
- Audio + text multimodal merge in one turn  
- Web microphone upload  
