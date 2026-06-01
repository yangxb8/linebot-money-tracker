# linebot-money-tracker

A minimal LINE chat bot sample built with FastAPI, LINE Messaging API, and Gemini AI integration.

## Requirements

- Python 3.11+
- LINE channel credentials
- Gemini API key and endpoint URL

## Environment Variables

Set the following environment variables before running the app:

- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `GEMINI_API_KEY`
- `GEMINI_API_URL`

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
  --set-env-vars LINE_CHANNEL_SECRET=$LINE_CHANNEL_SECRET,LINE_CHANNEL_ACCESS_TOKEN=$LINE_CHANNEL_ACCESS_TOKEN,GEMINI_API_KEY=$GEMINI_API_KEY,GEMINI_API_URL=$GEMINI_API_URL
```

Then configure the LINE webhook URL to `https://<your-service-url>/callback`.

## Docker

A simple Dockerfile is provided for container deployment.

## Testing

Run all tests:

```bash
python -m pytest -q
```
