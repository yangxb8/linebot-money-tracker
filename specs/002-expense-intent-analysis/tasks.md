# Tasks: Expense Intent Analysis

**Feature**: `002-expense-intent-analysis`

## Phase 1: Setup

- [X] T001 Add research document in specs/002-expense-intent-analysis/research.md
- [X] T002 [P] Add optional OCR dependencies in requirements.txt (pytesseract, Pillow)
- [X] T003 Create service skeleton: services/ocr.py, services/receipt_parser.py, services/ai_assist.py

## Phase 2: Foundational

- [X] T004 [P] Implement `services/ocr.py` with local `pytesseract` backend and optional Google Document AI client
- [X] T005 [P] Implement `services/receipt_parser.py` deterministic parser for amounts and currencies
- [X] T006 Implement `services/ai_assist.py` wrapper to call Gemini with compact OCR text and strict JSON schema
- [X] T007 Add `services/intent.py` to detect expense intent from text and classify events

## Phase 3: User Story 1 - Text expense detection (P1)

- [X] T008 [US1] Implement text parsing helpers in `services/intent.py` and `services/receipt_parser.py` for free-form text
- [X] T009 [US1] Integrate text intent flow into `main.py` webhook handler (parse -> respond) at `main.py`
- [X] T010 [US1] Unit tests for text parsing in tests/test_intent_text.py

## Phase 4: User Story 2 - Image receipt extraction (P2)

- [X] T011 [US2] Integrate OCR pipeline into `main.py` for image events and normalize OCR output
- [X] T012 [US2] Apply deterministic parsing to OCR text and return parsed items in plain text
- [X] T013 [US2] Add AI-assisted disambiguation call in `services/ai_assist.py` when parser confidence is low
- [X] T014 [US2] Integration tests for image -> parsed output in tests/test_image_receipts.py

## Phase 5: User Story 3 - Unsupported requests (P3)

- [X] T015 [US3] Implement fixed canned reply for unsupported/non-expense events in `main.py` using constants in `main.py`
- [X] T016 [US3] Unit tests asserting canned reply for non-text/non-image events in tests/test_unsupported_events.py

## Final Phase: Polish & Cross-Cutting

- [X] T017 Update README.md with new env vars and optional OCR deployment notes
- [X] T018 Add sample receipt corpus under `specs/002-expense-intent-analysis/samples/`
- [X] T019 Add jsonschema validation for AI responses in `services/ai_assist.py`
- [X] T020 Add CI job and run tests in GitHub Actions

## Dependencies

- `T004` and `T005` can be implemented in parallel (both create parsing building blocks). Marked `[P]` above.
- `T011` depends on `T004` and `T005`.
- `T013` depends on `T006` and `T005`.

## Parallel Opportunities

- Implement `services/ocr.py` and `services/receipt_parser.py` in parallel.
- Unit tests for parser and AI assist can be developed concurrently with implementation once interfaces are defined.

## Implementation Strategy

- MVP-first: implement deterministic parsing and text intent (US1) first to validate the UX.
- Add OCR + AI-assist (US2) next, using the minimal prompt that sends only OCR text to Gemini.
- Keep AI usage minimized by returning deterministic parser results when confidence high; only call AI for ambiguous cases.

## Follow-up

- [X] T021 Use LLM-based intent classification in `services/intent.py` for text and image inputs (reject non-receipt images like pet photos)
- [X] T022 Reorder image pipeline: OCR/parse before Gemini image intent; skip intent when OCR finds items (`services/message_handler.py`)
- [X] T023 Add receipt amount normalization: tax + discount proportional allocation (`services/receipt_normalize.py`, [contracts/receipt-amount-semantics.md](./contracts/receipt-amount-semantics.md))
- [X] T024 Update LLM assist prompts for cash-out amounts and 合計 sum validation (`services/ai_assist.py`)
- [X] T025 Add unit tests for My Basket-style receipts and total-only fallback (`tests/test_receipt_normalize.py`)
