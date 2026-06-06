# Quickstart: Local Development & Cloud Run

**Feature**: 003-local-dev-setup  
**Time target**: ~15 minutes for console setup; ~30 minutes including optional OCR

Production target: **Google Cloud Run**. Primary local workflow: **console harness** (no LINE account required).

---

## 1. Install

```bash
git clone <repo-url>
cd linebot-money-tracker
python -m pip install -r requirements.txt
```

**Required**: Python 3.11+, pip, Git

---

## 2. Configure (console mode — minimum)

```bash
cp .env.example .env
```

Edit `.env` — for console testing you only need:

```
GEMINI_API_KEY=your-gemini-api-key
```

Get a key from [Google AI Studio](https://aistudio.google.com/).

---

## 3. Run automated tests

```bash
python -m pytest -q
```

No real API keys required (tests use mocks).

---

## 4. Local console testing (primary workflow)

Simulate LINE messages without a LINE channel or tunnel:

```bash
# Text expense
python local_run.py --text "Lunch 1200 yen"

# Receipt image
python local_run.py --image path/to/receipt.jpg
```

| What | Where |
| ---- | ----- |
| **Bot reply** | printed to **stdout** (same text LINE users would see) |
| **Debug detail** | application **logs** (OCR, intent, parsing) |

Neither command calls the LINE Messaging API.

Full contract: [contracts/local-console.md](./contracts/local-console.md)

---

## 5. Optional — receipt OCR (Japanese)

**Local Tesseract** (free):

| OS | Install |
| -- | ------- |
| Windows | `winget install UB-Mannheim.TesseractOCR` |
| macOS | `brew install tesseract tesseract-lang` |
| Linux | `sudo apt install tesseract-ocr tesseract-ocr-jpn` |

Default: `TESSERACT_LANG=jpn+eng` in `.env`

**Document AI** (better accuracy, GCP):

```bash
gcloud auth application-default login
```

Add to `.env`:
```
DOCUMENT_AI_PROJECT_ID=your-project
DOCUMENT_AI_PROCESSOR_ID=your-processor-id
DOCUMENT_AI_LOCATION=asia-northeast1
```

---

## 6. Optional — webhook server + real LINE

Requires LINE Developers Console credentials in `.env`:

```
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
GEMINI_API_KEY=...
```

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
ngrok http 8000
```

Set LINE webhook to `https://<ngrok-host>/callback`.

Details: [contracts/local-development.md](./contracts/local-development.md)

---

## 7. Deploy to Cloud Run

Full steps: [contracts/cloud-run-deployment.md](./contracts/cloud-run-deployment.md)

```bash
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/linebot-money-tracker
gcloud run deploy linebot-money-tracker \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/linebot-money-tracker \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars LINE_CHANNEL_SECRET=...,LINE_CHANNEL_ACCESS_TOKEN=...,GEMINI_API_KEY=...
```

---

## Setup profiles

| Profile | Command | Env vars |
| ------- | ------- | -------- |
| **Console (default)** | `local_run.py --text/--image` | `GEMINI_API_KEY` |
| Unit tests | `pytest -q` | mocked |
| Webhook + LINE | `uvicorn main:app` + ngrok | LINE_* + GEMINI_* |
| Cloud Run | container deploy | LINE_* + GEMINI_* |

---

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| `Missing GEMINI_API_KEY` | Set in `.env` |
| Console works but webhook fails | Add LINE vars to `.env` |
| Tesseract not found | Install engine; check PATH |
| No OCR on image | Install Tesseract or configure Document AI |
| ngrok URL changed | Update LINE webhook URL |

---

## Related documents

- [Local console contract](./contracts/local-console.md)
- [Environment variables](./contracts/environment-variables.md)
- [Cloud Run deployment](./contracts/cloud-run-deployment.md)
- [Data model](./data-model.md)
