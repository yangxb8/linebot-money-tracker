# Research: Local Development & Cloud Run Setup

**Feature**: 003-local-dev-setup  
**Date**: 2026-06-06 (updated after clarifications)

## 1. Primary local testing workflow

**Decision**: Console harness (`local_run.py`) simulates LINE messages; prints reply to stdout; no LINE Messaging API calls.

**Rationale**: Clarified in spec session 2026-06-06. Fastest iteration for parsing, intent, and OCR without ngrok or LINE channel setup.

**Alternatives considered**:
- ngrok-only local testing — rejected as primary; kept as optional P3 path
- pytest-only dev — insufficient for manual receipt image testing with real Gemini/OCR

## 2. Console environment requirements

**Decision**: Console mode requires only `GEMINI_API_KEY` (+ optional OCR vars). LINE vars required only for webhook server and Cloud Run.

**Rationale**: Console does not validate webhook signatures or send LINE replies.

**Alternatives considered**:
- Require all three vars everywhere — rejected; blocks devs without LINE channel

## 3. Console CLI interface

**Decision**: Single command, mutually exclusive flags: `--text "..."` or `--image <path>`.

**Rationale**: Scriptable, documented, easy to copy-paste in quickstart.

**Alternatives considered**:
- Interactive REPL — rejected per clarification
- Both flags and REPL — rejected; YAGNI

## 4. Console output separation

**Decision**: stdout = final reply text only; application logs (INFO) carry OCR/intent/parsing debug detail.

**Rationale**: User chose reply-only output; logs already configured via `logging.basicConfig` in `main.py`.

**Alternatives considered**:
- Reply + debug on stdout — rejected
- JSON output — rejected

## 5. Shared processing pipeline

**Decision**: Extract `services/message_handler.py` with `process_text_message` and `process_image_message`; both `main.py` and `local_run.py` call it.

**Rationale**: Constitution requires eliminating duplicated logic; guarantees console output matches production replies.

**Alternatives considered**:
- Duplicate logic in CLI — rejected
- HTTP self-call to localhost — rejected; unnecessary coupling

## 6. Environment file loading

**Decision**: Add `python-dotenv`; load `.env` in `local_run.py` and `main.py` before env validation.

**Rationale**: FR-009 `.env.example`; standard local DX on Windows/macOS/Linux.

**Alternatives considered**:
- Document export-only — rejected for Windows friction

## 7. Deferred LINE validation in webhook server

**Decision**: Move LINE env checks from module import time to FastAPI lifespan startup in `main.py`.

**Rationale**: Enables importing handler modules in tests without LINE vars; clearer separation of console vs server profiles.

**Alternatives considered**:
- Separate `server.py` entry point — rejected; keep single `main.py` for Cloud Run CMD

## 8. HTTPS tunnel (optional integration)

**Decision**: Document ngrok as primary tunnel example; Cloudflare Tunnel as alternative. Optional P3 — not required for console workflow.

**Rationale**: Unchanged from prior research; still needed for real LINE end-to-end tests.

## 9. Cloud Run deployment

**Decision**: Same env var names; full LINE + Gemini on Cloud Run; Tesseract preinstalled in Docker image.

**Rationale**: Production parity with current Dockerfile and deployment docs.

## 10. Automated tests without external services

**Decision**: `python -m pytest -q` remains the unit test entry point; console harness tests mock Gemini/OCR layers.

**Rationale**: SC-003; existing test pattern with `os.environ.setdefault`.
