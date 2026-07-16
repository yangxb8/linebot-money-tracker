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

## Optional — usage limits (webhook, console, Cloud Run)

Active when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set. Console: `python local_run.py --skip-usage-limits` bypasses checks.

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `USAGE_TIER_FREE_MONTHLY_TOTAL` | `300` | Free-tier LLM invocations per calendar month (all operation types) |
| `USAGE_TIER_FREE_RECEIPT_MONTHLY` | `100` | Free-tier receipt analyses per month (subset of monthly total) |
| `USAGE_RATE_LIMIT_PER_MINUTE` | `10` | Max LLM-backed messages per sender per minute |
| `USAGE_RATE_LIMIT_PER_DAY` | `100` | Max LLM-backed messages per sender per day |
| `USAGE_MAX_TEXT_WORDS` | `1000` | Reject inbound text over this word count before LLM |
| `USAGE_MAX_IMAGE_BYTES` | `10485760` | Reject inbound images over this size (10 MiB) before LLM |

## Optional — expense dashboard link (webhook, console, Cloud Run)

When users ask for the web app or dashboard in chat, the bot replies with this URL. Use the LIFF URL from the LINE Login channel (same value as rich menu setup).

| Variable | Required | Purpose |
| -------- | -------- | ------- |
| `DASHBOARD_LIFF_URL` | No | Full LIFF URL (e.g. `https://liff.line.me/<LIFF_ID>`) returned when users request the dashboard |

## Optional — OCR (all profiles)

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `TESSERACT_LANG` | `jpn+eng` | Tesseract languages for local OCR |
| `DOCUMENT_AI_PROJECT_ID` | — | GCP project (fallback: `GOOGLE_CLOUD_PROJECT`) |
| `DOCUMENT_AI_PROCESSOR_ID` | — | Document AI processor ID |
| `DOCUMENT_AI_LOCATION` | — | Processor region (e.g. `asia-northeast1`) |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project fallback |

## Optional — Sentry (webhook, console, Cloud Run)

When `SENTRY_DSN` is set, the app initializes the Sentry SDK and creates Sentry issues for ERROR+ stdlib log records only (full log forwarding is off). FastAPI request errors are captured automatically.

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `SENTRY_DSN` | — | Project DSN from Sentry; omit to disable |
| `SENTRY_ENVIRONMENT` | — | Environment tag (falls back to `ENV` if set) |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | Performance tracing sample rate (`0.0`–`1.0`) |

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
