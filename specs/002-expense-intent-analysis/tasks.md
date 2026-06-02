# Tasks: Expense Intent Analysis

**Feature**: `002-expense-intent-analysis`

## Phase 1: Setup

- [ ] T001 Add research document in specs/002-expense-intent-analysis/research.md
- [ ] T002 [P] Add optional OCR dependencies in requirements.txt (pytesseract, Pillow)
- [ ] T003 Create service skeleton: services/ocr.py, services/receipt_parser.py, services/ai_assist.py

## Phase 2: Foundational

- [ ] T004 [P] Implement `services/ocr.py` with local `pytesseract` backend and optional Google Vision client
- [ ] T005 [P] Implement `services/receipt_parser.py` deterministic parser for amounts and currencies
- [ ] T006 Implement `services/ai_assist.py` wrapper to call Gemini with compact OCR text and strict JSON schema
- [ ] T007 Add `services/intent.py` to detect expense intent from text and classify events

## Phase 3: User Story 1 - Text expense detection (P1)

- [ ] T008 [US1] Implement text parsing helpers in `services/intent.py` and `services/receipt_parser.py` for free-form text
- [ ] T009 [US1] Integrate text intent flow into `main.py` webhook handler (parse -> respond) at `main.py`
- [ ] T010 [US1] Unit tests for text parsing in tests/test_intent_text.py

## Phase 4: User Story 2 - Image receipt extraction (P2)

- [ ] T011 [US2] Integrate OCR pipeline into `main.py` for image events and normalize OCR output
- [ ] T012 [US2] Apply deterministic parsing to OCR text and return parsed items in plain text
- [ ] T013 [US2] Add AI-assisted disambiguation call in `services/ai_assist.py` when parser confidence is low
- [ ] T014 [US2] Integration tests for image -> parsed output in tests/test_image_receipts.py

## Phase 5: User Story 3 - Unsupported requests (P3)

- [ ] T015 [US3] Implement fixed canned reply for unsupported/non-expense events in `main.py` using constants in `main.py`
- [ ] T016 [US3] Unit tests asserting canned reply for non-text/non-image events in tests/test_unsupported_events.py

## Final Phase: Polish & Cross-Cutting

- [ ] T017 Update README.md with new env vars and optional OCR deployment notes
- [ ] T018 Add sample receipt corpus under `specs/002-expense-intent-analysis/samples/`
- [ ] T019 Add jsonschema validation for AI responses in `services/ai_assist.py`
- [ ] T020 Add CI job and run tests in GitHub Actions

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
