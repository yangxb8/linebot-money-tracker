# Contract: Environment Variables

**Feature**: 003-local-dev-setup  
**Applies to**: Local console, webhook server, and Google Cloud Run

Variable names are identical across all targets; **required** set depends on profile.

## Console harness (`local_run.py`)

| Variable | Required | Secret | Purpose |
| -------- | -------- | ------ | ------- |
| `GEMINI_API_KEY` | **Yes** | Yes | Intent classification and AI-assisted parsing |

LINE variables are **not** required for console mode.

## Webhook server (`uvicorn main:app`) and Cloud Run

| Variable | Required | Secret | Purpose |
| -------- | -------- | ------ | ------- |
| `LINE_CHANNEL_SECRET` | **Yes** | Yes | Validates LINE webhook signatures |
| `LINE_CHANNEL_ACCESS_TOKEN` | **Yes** | Yes | Sends reply messages |
| `GEMINI_API_KEY` | **Yes** | Yes | Intent and AI-assisted parsing |

## Optional — OCR (all profiles)

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `TESSERACT_LANG` | `jpn+eng` | Tesseract languages for local OCR |
| `DOCUMENT_AI_PROJECT_ID` | — | GCP project (fallback: `GOOGLE_CLOUD_PROJECT`) |
| `DOCUMENT_AI_PROCESSOR_ID` | — | Document AI processor ID |
| `DOCUMENT_AI_LOCATION` | — | Processor region (e.g. `asia-northeast1`) |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project fallback |

## Local setup

1. Copy `.env.example` to `.env`
2. For console testing: set `GEMINI_API_KEY` only
3. For webhook server: add LINE credentials too
4. For Document AI locally: `gcloud auth application-default login` + Document AI vars

## Cloud Run setup

```bash
--set-env-vars LINE_CHANNEL_SECRET=...,LINE_CHANNEL_ACCESS_TOKEN=...,GEMINI_API_KEY=...
```

Add `DOCUMENT_AI_*` for cloud OCR fallback in production.

## Obtaining credentials

- **Gemini**: [Google AI Studio](https://aistudio.google.com/)
- **LINE**: [LINE Developers Console](https://developers.line.biz/) — channel secret and access token (webhook/Cloud Run only)
