# Data Model: Local Development & Cloud Run Setup

**Feature**: 003-local-dev-setup (updated)

## Entities

### EnvironmentVariable

| name | required (console) | required (webhook) | secret |
| ---- | ------------------ | ------------------ | ------ |
| `GEMINI_API_KEY` | yes | yes | yes |
| `LINE_CHANNEL_SECRET` | no | yes | yes |
| `LINE_CHANNEL_ACCESS_TOKEN` | no | yes | yes |
| `TESSERACT_LANG` | no | no | no |
| `DOCUMENT_AI_*` | no | no | no |

### SetupProfile

| Profile | Entry point | Required env | Output |
| ------- | ----------- | ------------ | ------ |
| **Local Console** | `python local_run.py --text ...` or `--image ...` | `GEMINI_API_KEY` | Reply on stdout; logs to console |
| **Webhook server** | `uvicorn main:app` | LINE_* + GEMINI_* | HTTP 200; LINE reply API |
| **Unit tests** | `pytest -q` | mocked in tests | test results |
| **Cloud Run** | container CMD | LINE_* + GEMINI_* | HTTPS webhook + LINE replies |

### SimulatedMessage

Input model for console harness (not persisted).

| Field | Type | Source |
| ----- | ---- | ------ |
| kind | `text` \| `image` | CLI flag |
| text | string | `--text` value |
| image_path | path | `--image` value |
| image_bytes | bytes | read from file at runtime |
| mime_type | string | guessed from bytes |

**Validation**:
- Exactly one of `--text` or `--image` must be provided
- Image path must exist and be readable
- Text must be non-empty

### BotReply

Output of shared message handler (same for console and LINE).

| Field | Description |
| ----- | ----------- |
| text | Final user-facing reply string |
| source | `expense_parse` \| `gemini_fallback` \| `unsupported` \| `error` |

Console prints `text` to stdout only. Webhook sends `text` via LINE Messaging API.

## State Transitions

```text
[Clone] → [pip install] → [copy .env.example → .env, set GEMINI_API_KEY]
     → [local_run.py --text ...]  → stdout reply
     → [local_run.py --image ...] → stdout reply (optional Tesseract/Document AI)
     → (optional) [uvicorn main:app + ngrok + LINE webhook]
     → [gcloud run deploy] → production
```

## Relationships

- `SimulatedMessage` → `message_handler.process_*` → `BotReply`
- LINE webhook event → same handler → `BotReply` → LINE API (webhook only)
