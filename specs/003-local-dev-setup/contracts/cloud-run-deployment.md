# Contract: Cloud Run Deployment

**Feature**: 003-local-dev-setup  
**Production endpoint**: `POST https://<service-url>/callback`

## Prerequisites

- Validate expense flows locally first with [local console harness](./local-console.md) (`GEMINI_API_KEY` only)
- Google Cloud project with billing enabled
- `gcloud` CLI installed and authenticated
- Docker (for local image build) or Cloud Build enabled
- LINE and Gemini credentials (same variables as local)

## Environment parity

Cloud Run MUST use the **same variable names** as local development. See [environment-variables.md](./environment-variables.md).

Minimum deploy variables:
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `GEMINI_API_KEY`

Optional (recommended for production receipt OCR):
- `DOCUMENT_AI_PROJECT_ID`
- `DOCUMENT_AI_PROCESSOR_ID`
- `DOCUMENT_AI_LOCATION`

The container image includes Tesseract with Japanese support; `TESSERACT_LANG` defaults to `jpn+eng` inside the image.

## Deployment workflow

### 1. Build and push image

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id

gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/linebot-money-tracker
```

Or build locally:
```bash
docker build -t linebot-money-tracker .
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy linebot-money-tracker \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/linebot-money-tracker \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars LINE_CHANNEL_SECRET=$LINE_CHANNEL_SECRET,\
LINE_CHANNEL_ACCESS_TOKEN=$LINE_CHANNEL_ACCESS_TOKEN,\
GEMINI_API_KEY=$GEMINI_API_KEY,\
DOCUMENT_AI_PROJECT_ID=$GOOGLE_CLOUD_PROJECT,\
DOCUMENT_AI_PROCESSOR_ID=$DOCUMENT_AI_PROCESSOR_ID,\
DOCUMENT_AI_LOCATION=asia-northeast1
```

Adjust region to match your Document AI processor location.

### 3. Configure LINE webhook

1. Copy the Cloud Run service URL from deploy output
2. Set LINE webhook to: `https://<service-url>/callback`
3. Disable the local tunnel webhook when switching to production

### 4. IAM for Document AI (if used)

Grant the Cloud Run service account:
- `roles/documentai.apiUser` (or custom role with `documentai.processors.processOnlineDocument`)

Create an OCR processor in [Document AI console](https://console.cloud.google.com/ai/document-ai/processors) in the same region as Cloud Run.

## Local vs Cloud Run differences

| Aspect | Local | Cloud Run |
| ------ | ----- | --------- |
| Config | `.env` file | `--set-env-vars` or console |
| HTTPS | Via tunnel | Provided by Cloud Run |
| Tesseract | Optional install | Preinstalled in Dockerfile |
| Document AI auth | `gcloud auth application-default login` | Service account (automatic) |
| Webhook URL | Changes with tunnel | Stable service URL |

## Acceptance checks

| Check | Expected |
| ----- | -------- |
| Deploy succeeds | Service URL returned |
| Health | POST to `/callback` with valid LINE signature returns 200 |
| LINE message | Bot replies using production URL |
| Receipt image | OCR + parsing works (Tesseract or Document AI fallback) |

## Rollback

Redeploy a previous image revision from Cloud Run console or:

```bash
gcloud run services update-traffic linebot-money-tracker --to-revisions=<previous-revision>=100
```
