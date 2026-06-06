# linebot-money-tracker

A LINE expense bot built with FastAPI, LINE Messaging API, and Gemini AI.

**Full setup guide:** [specs/003-local-dev-setup/quickstart.md](specs/003-local-dev-setup/quickstart.md)

## Quick start (local console — no LINE account needed)

```bash
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env — set GEMINI_API_KEY only for console mode

python local_run.py --text "Lunch 1200 yen"
python local_run.py --image path/to/receipt.jpg
```

The bot reply prints to **stdout**. Debug detail (OCR, intent) appears in **logs**. No LINE Messaging API calls are made.

## Requirements

- Python 3.11+ (3.13 recommended)
- Gemini API key ([Google AI Studio](https://aistudio.google.com/))

Optional: LINE credentials (webhook server), Tesseract + `jpn` (local OCR), gcloud (Document AI / Cloud Run)

## Environment variables

Copy [`.env.example`](.env.example) to `.env`.

| Profile | Required variables |
| ------- | ------------------ |
| **Console** (`local_run.py`) | `GEMINI_API_KEY` |
| **Console + persistence** | `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| **Webhook / Cloud Run** | `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `GEMINI_API_KEY` |
| **Webhook + persistence** | Above plus `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |

Optional persistence: `LOCAL_LINE_USER_ID` (console mode user id, default `local-dev-user`)

See [Supabase expense storage quickstart](specs/004-supabase-expense-storage/quickstart.md) for migration and verification steps.

Optional OCR: `TESSERACT_LANG`, `DOCUMENT_AI_PROJECT_ID`, `DOCUMENT_AI_PROCESSOR_ID`, `DOCUMENT_AI_LOCATION`

See [environment variables contract](specs/003-local-dev-setup/contracts/environment-variables.md).

## Webhook server (optional)

For real LINE integration or Cloud Run parity:

```bash
# Set LINE_* and GEMINI_* in .env, then:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Optional: expose via [ngrok](https://ngrok.com/) and set LINE webhook to `https://<tunnel>/callback`.

Details: [local development contract](specs/003-local-dev-setup/contracts/local-development.md)

## Cloud Run deployment

Production target. Same env var names as local webhook server.

```bash
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/linebot-money-tracker
gcloud run deploy linebot-money-tracker \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/linebot-money-tracker \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars LINE_CHANNEL_SECRET=...,LINE_CHANNEL_ACCESS_TOKEN=...,GEMINI_API_KEY=...
```

Full steps: [Cloud Run deployment contract](specs/003-local-dev-setup/contracts/cloud-run-deployment.md)

## Docker

The Dockerfile installs `tesseract-ocr` and `tesseract-ocr-jpn` for Japanese receipt OCR. Document AI is the cloud fallback when configured.

## Testing

```bash
python -m pytest -q
```

Tests use mock credentials; no LINE or Gemini keys required.
