# Contract: Local Webhook Server & Optional LINE Integration

**Feature**: 003-local-dev-setup  
**Entry point**: `uvicorn main:app --host 0.0.0.0 --port 8000`  
**Endpoint**: `POST /callback`

> For day-to-day development, prefer the [local console harness](./local-console.md) — it requires only `GEMINI_API_KEY` and no tunnel.

## Prerequisites

**Required software**: Python 3.11+, pip, Git  
**Required env vars**: `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `GEMINI_API_KEY`

**Optional**: ngrok/Cloudflare Tunnel for real LINE delivery; Tesseract/Document AI for receipt OCR

## Workflow

### 1. Install and configure

```bash
python -m pip install -r requirements.txt
cp .env.example .env
# Set LINE_* and GEMINI_API_KEY in .env
```

### 2. Start server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Missing LINE or Gemini vars → startup fails with explicit list.

### 3. Optional — connect real LINE via tunnel

```bash
ngrok http 8000
```

Set LINE webhook URL to `https://<tunnel-host>/callback`.

### 4. Run tests (no LINE needed)

```bash
python -m pytest -q
```

## Acceptance checks

| Check | Expected |
| ----- | -------- |
| Missing LINE env at server start | Fail with variable names listed |
| POST /callback with valid signature | 200 OK |
| LINE text message via tunnel | Reply in LINE chat |

## Related

- [Local console harness](./local-console.md) — primary dev workflow
- [Environment variables](./environment-variables.md)
