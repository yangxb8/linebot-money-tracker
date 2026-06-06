# linebot-money-tracker

A minimal LINE chat bot sample built with FastAPI, LINE Messaging API, and Gemini AI integration.

## Requirements

- Python 3.11+
- LINE channel credentials
- Gemini API key and endpoint URL

## Environment Variables

Set the following environment variables before running the app:

### Required

- `LINE_CHANNEL_SECRET` — LINE Messaging API channel secret
- `LINE_CHANNEL_ACCESS_TOKEN` — LINE Messaging API channel access token
- `GEMINI_API_KEY` — Google Gemini API key for AI-assisted parsing

### Optional (OCR)

The bot uses local OCR (`pytesseract`) by default when Tesseract is installed. If local OCR fails or is unavailable, it falls back to **Google Document AI**.

| Variable | Description |
|----------|-------------|
| `DOCUMENT_AI_PROJECT_ID` | GCP project ID (falls back to `GOOGLE_CLOUD_PROJECT`) |
| `DOCUMENT_AI_PROCESSOR_ID` | Document AI OCR processor ID |
| `DOCUMENT_AI_LOCATION` | Processor region (default: `us`; use `asia-northeast1` for Japan) |
| `TESSERACT_LANG` | Tesseract language(s) for local OCR (default: `jpn+eng`) |

Document AI requires Application Default Credentials in the deployment environment (e.g. Cloud Run service account with `documentai.apiUser` role).

Local development with pytesseract also requires the [Tesseract OCR engine](https://github.com/tesseract-ocr/tesseract) and language packs (e.g. `tesseract-ocr-jpn` on Debian/Ubuntu).

### Japanese receipt tips

- **Local OCR**: the Docker image installs `tesseract-ocr-jpn`. Default `TESSERACT_LANG=jpn+eng` covers mixed Japanese/English labels (store name, 合計, tax lines).
- **Production OCR**: prefer **Document AI** in `asia-northeast1` with an OCR or Invoice parser processor — accuracy on Japanese receipts is generally better than Tesseract, especially for photos and thermal prints.
- **Parsing**: the deterministic parser normalizes full-width digits (`１２３４` → `1234`) and recognizes `円`, `¥`, and `￥`. Ambiguous OCR output still falls back to Gemini via `services/ai_assist.py`.
- **Photos**: receipt photos work best when the image is flat, well-lit, and fills the frame. Crooked or blurry shots hurt Tesseract more than Document AI.

## Local Development

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the app locally:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Expose the local webhook to LINE with a tunnel during development, such as ngrok.

## Deployment

This service is designed for cloud deployment as a webhook endpoint. Recommended low-cost platforms include:

- Google Cloud Run
- Railway
- Render
- Fly.io

### Google Cloud Run (recommended)

Build and deploy using Docker:

```bash
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/linebot-money-tracker

gcloud run deploy linebot-money-tracker \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/linebot-money-tracker \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars LINE_CHANNEL_SECRET=$LINE_CHANNEL_SECRET,LINE_CHANNEL_ACCESS_TOKEN=$LINE_CHANNEL_ACCESS_TOKEN,GEMINI_API_KEY=$GEMINI_API_KEY
```

Then configure the LINE webhook URL to `https://<your-service-url>/callback`.

For image receipt OCR on Cloud Run, grant the service account access to Document AI and set `DOCUMENT_AI_PROJECT_ID`, `DOCUMENT_AI_PROCESSOR_ID`, and optionally `DOCUMENT_AI_LOCATION`. Create an OCR processor in the [Document AI console](https://console.cloud.google.com/ai/document-ai/processors).

## Docker

A simple Dockerfile is provided for container deployment. It installs `tesseract-ocr` and `tesseract-ocr-jpn` so `pytesseract` can OCR Japanese receipts inside the container. If Tesseract is unavailable, the app falls back to Document AI when configured.

## Testing

Run all tests:

```bash
python -m pytest -q
```
