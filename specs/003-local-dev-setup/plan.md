# Implementation Plan: Local Development & Cloud Run Setup

**Branch**: `003-local-dev-setup` | **Date**: 2026-06-06 | **Spec**: `/specs/003-local-dev-setup/spec.md`

**Input**: Feature specification from `/specs/003-local-dev-setup/spec.md` (includes clarifications for console harness)

## Summary

Enable fast local development via a **console harness** that simulates LINE text/image messages, runs the same expense-processing pipeline as production, and prints only the final reply to stdout (logs carry debug detail). Refactor message handling out of `main.py` into a shared service module. Split environment validation: console mode requires only `GEMINI_API_KEY`; webhook server and Cloud Run require full LINE + Gemini credentials. Deliver `.env.example`, updated quickstart, and optional `python-dotenv` loading.

## Technical Context

**Language/Version**: Python 3.13 (Dockerfile/CI); Python 3.11+ locally

**Primary Dependencies**: FastAPI, uvicorn, line-bot-sdk, google-genai, pytest; optional pytesseract, google-cloud-documentai, python-dotenv

**Storage**: N/A

**Testing**: pytest for unit/integration; new tests for console CLI and shared handler; existing webhook tests unchanged

**Target Platform**: Local developer machines + Google Cloud Run

**Project Type**: web-service with CLI dev harness

**Performance Goals**: Console command returns within same bounds as webhook path (~5s for expense analysis)

**Constraints**:
- Console stdout = final reply only; logs at INFO for OCR/intent/parsing
- No LINE API calls in console mode
- Same reply text as production for equivalent inputs
- Secrets via `.env` (local) or Cloud Run env vars

**Scale/Scope**: Dev tooling + documentation refactor; one new CLI entry point + handler extraction

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Extract shared `process_text` / `process_image` handler; eliminate duplication between webhook and console |
| Test-First Delivery | Tests for console CLI, handler module, and split env validation before/alongside implementation |
| User Experience Consistency | Console prints identical reply strings as LINE would receive |
| Performance & Reliability | Reuse async handler; same error/fallback messages |
| Observability & Feedback | Logging unchanged; stdout separated from logs |
| Secrets | `.env.example` only; `.env` gitignored |

**Post-design re-check**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/003-local-dev-setup/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── environment-variables.md
│   ├── local-console.md          # new — console harness contract
│   ├── local-development.md      # webhook server + optional tunnel
│   └── cloud-run-deployment.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
main.py                 # webhook only; lazy LINE env validation
local_run.py            # new — CLI: --text / --image, stdout reply
.env.example            # new
services/
  message_handler.py    # new — shared text/image processing → reply str
  (existing services unchanged)
tests/
  test_message_handler.py
  test_local_run.py
```

**Structure Decision**: Add `local_run.py` at repo root (matches `main.py` pattern). Extract processing logic to `services/message_handler.py` so webhook and console share one code path.

## Implementation Approach

### 1. Extract shared message handler (`services/message_handler.py`)

Move text and image processing from `main.py` into async functions:

```python
async def process_text_message(text: str, gemini: GeminiClient) -> str: ...
async def process_image_message(image_bytes: bytes, gemini: GeminiClient, mime_type: str) -> str: ...
```

Returns the reply string (expense summary, canned unsupported, or error message). Uses existing intent, parser, OCR, and AI assist services.

### 2. Refactor `main.py`

- Defer LINE credential validation until app startup (lifespan), not module import — allows importing without LINE vars for tests/console tooling if needed
- `handle_callback` calls shared handler, then sends reply via LINE API
- Keep constants (`CANNED_UNSUPPORTED_REPLY`, etc.) in handler module or shared config

### 3. Add console harness (`local_run.py`)

```bash
python local_run.py --text "Lunch 1200 yen"
python local_run.py --image path/to/receipt.jpg
```

- argparse with mutually exclusive `--text` / `--image`
- Validate only `GEMINI_API_KEY` at startup
- Load `.env` via `python-dotenv` if present
- `asyncio.run()` → shared handler → `print(reply)` to stdout
- Exit code 1 on usage error or processing exception; exit 0 on success
- Logging to stderr/default log config at INFO

### 4. Environment and documentation

- `.env.example` with all vars, commented by profile (console vs webhook)
- `python-dotenv` in requirements.txt; load in `local_run.py` and optionally `main.py`
- Update `README.md` to link quickstart; console harness as step 1
- Update `quickstart.md` and contracts

### 5. Tests

- `test_message_handler.py` — text/image paths with mocked Gemini/OCR
- `test_local_run.py` — CLI args, stdout capture, no LINE API mock needed
- Ensure existing `test_line_webhook.py` still passes after refactor

## Risks and Open Questions

- **Import-time side effects in `main.py`**: Currently exits if LINE vars missing at import — must refactor before console can coexist cleanly.
- **Image intent uses Gemini multimodal**: Console image tests need real or mocked Gemini unless tests patch intent layer.
- **Plan vs persistence constitution note**: Constitution mentions expense persistence; current app is stateless — out of scope for this feature.

## Next Steps

Run `/speckit-tasks` then `/speckit-implement` to build handler extraction, `local_run.py`, `.env.example`, and documentation updates.
