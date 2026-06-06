# Tasks: Local Development & Cloud Run Setup

**Input**: Design documents from `/specs/003-local-dev-setup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks grouped by user story. MVP = User Story 1 (local console harness).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to spec user stories (US1–US5)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and environment template for console and webhook profiles

- [X] T001 Add `python-dotenv` to `requirements.txt`
- [X] T002 [P] Create `.env.example` at repo root with console and webhook variable groups per `specs/003-local-dev-setup/contracts/environment-variables.md`
- [X] T003 [P] Add `services/env_loader.py` to load `.env` via dotenv before reading environment variables

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared message handler and webhook refactor — MUST complete before user story phases

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create `services/message_handler.py` with `process_text_message`, `process_image_message`, and shared reply constants (`CANNED_UNSUPPORTED_REPLY`, `ERROR_REPLY_TEXT`, `_format_expense_items`) extracted from `main.py`
- [X] T005 Refactor `main.py` to defer LINE + Gemini env validation to FastAPI lifespan startup (not module import) per `specs/003-local-dev-setup/research.md`
- [X] T006 Refactor `main.py` `handle_callback` to call `services/message_handler.py` and send the returned reply via LINE API only
- [X] T007 Update `tests/test_line_webhook.py` for deferred env validation and shared handler imports

**Checkpoint**: Shared pipeline ready — console and webhook can share one code path

---

## Phase 3: User Story 1 - Local Console Testing (Priority: P1) 🎯 MVP

**Goal**: Run `local_run.py --text` or `--image` with only `GEMINI_API_KEY`; print reply to stdout; no LINE API calls

**Independent Test**: `python local_run.py --text "Lunch 1200 yen"` prints expense summary; no LINE credentials required

### Implementation for User Story 1

- [X] T008 [P] [US1] Add unit tests for `process_text_message` and `process_image_message` in `tests/test_message_handler.py`
- [X] T009 [P] [US1] Add CLI tests for `--text`, `--image`, usage errors, and stdout-only output in `tests/test_local_run.py`
- [X] T010 [US1] Implement `local_run.py` with mutually exclusive `--text` and `--image` flags per `specs/003-local-dev-setup/contracts/local-console.md`
- [X] T011 [US1] Wire `local_run.py` to load `.env` via `services/env_loader.py`, validate only `GEMINI_API_KEY`, invoke shared handler, and `print()` reply to stdout in `local_run.py`

**Checkpoint**: Console harness fully functional for text and image inputs

---

## Phase 4: User Story 2 - Run Webhook Server Locally (Priority: P2)

**Goal**: Start `uvicorn main:app` locally with full LINE + Gemini env vars; fail fast with clear missing-var message

**Independent Test**: With all three required vars in `.env`, server starts on port 8000; missing LINE var exits with explicit list

### Implementation for User Story 2

- [X] T012 [US2] Load `.env` in `main.py` via `services/env_loader.py` before lifespan env validation in `main.py`
- [X] T013 [US2] Ensure lifespan startup validates `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, and `GEMINI_API_KEY` with explicit error message in `main.py`
- [X] T014 [US2] Add startup integration test or extend `tests/test_line_webhook.py` to verify server module loads when env vars are set in `tests/test_line_webhook.py`

**Checkpoint**: Webhook server starts locally with documented env profile

---

## Phase 5: User Story 4 - Receipt & Image Features Locally (Priority: P2)

**Goal**: Console `--image` path exercises OCR (Tesseract/Document AI) and prints expense output or clear errors

**Independent Test**: `python local_run.py --image <receipt.jpg>` prints detected expenses or explicit error when OCR unavailable

### Implementation for User Story 4

- [X] T015 [P] [US4] Add image-path tests with mocked OCR and intent in `tests/test_message_handler.py`
- [X] T016 [US4] Handle unreadable/missing image files with usage error and exit code 1 in `local_run.py`
- [X] T017 [US4] Verify `process_image_message` in `services/message_handler.py` reuses OCR → parse → AI assist fallback chain unchanged from prior `main.py` behavior

**Checkpoint**: Image receipt testing works via console without LINE

---

## Phase 6: User Story 3 - LINE Webhook Integration via Tunnel (Priority: P3)

**Goal**: Document optional end-to-end LINE testing with ngrok and webhook URL configuration

**Independent Test**: Developer follows quickstart tunnel steps and receives LINE replies (manual verification)

### Implementation for User Story 3

- [X] T018 [US3] Verify and update ngrok/tunnel steps in `specs/003-local-dev-setup/quickstart.md` and `specs/003-local-dev-setup/contracts/local-development.md`
- [X] T019 [US3] Add optional LINE integration section to root `README.md` linking to `specs/003-local-dev-setup/contracts/local-development.md`

**Checkpoint**: Optional real LINE path documented; not required for daily dev

---

## Phase 7: User Story 5 - Cloud Run Deployment (Priority: P3)

**Goal**: Document repeatable Cloud Run deploy with same env var names as local

**Independent Test**: Deploy steps in contract match `Dockerfile` CMD and env parity table

### Implementation for User Story 5

- [X] T020 [US5] Verify Cloud Run deploy commands and env var list in `specs/003-local-dev-setup/contracts/cloud-run-deployment.md`
- [X] T021 [US5] Add Cloud Run deployment summary to root `README.md` linking to `specs/003-local-dev-setup/contracts/cloud-run-deployment.md`

**Checkpoint**: Production deployment path documented and aligned with local env names

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation hub, README refresh, full test pass

- [X] T022 [P] Update root `README.md` to list console harness as primary local workflow and link `specs/003-local-dev-setup/quickstart.md`
- [X] T023 Run `python -m pytest -q` and fix any regressions across `tests/`
- [X] T024 Validate quickstart commands against implemented `local_run.py` flags in `specs/003-local-dev-setup/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — **MVP**
- **US2 (Phase 4)**: Depends on Phase 2; can parallel with US1 after T006
- **US4 (Phase 5)**: Depends on US1 (`local_run.py` + handler)
- **US3 (Phase 6)**: Documentation only — can parallel after US2
- **US5 (Phase 7)**: Documentation only — can parallel with US3
- **Polish (Phase 8)**: Depends on US1 minimum; complete after desired stories

### User Story Dependencies

| Story | Depends on | Notes |
| ----- | ---------- | ----- |
| US1 (P1) | Foundational | MVP — console harness |
| US2 (P2) | Foundational | Webhook server startup |
| US4 (P2) | US1 | Image flag on console |
| US3 (P3) | US2 (soft) | Docs for tunnel + running server |
| US5 (P3) | None (docs) | Cloud Run contract |

### Parallel Opportunities

**Phase 1**: T002 and T003 in parallel after T001

**Phase 3 (US1)**: T008 and T009 in parallel before T010

**Phase 5 (US4)**: T015 parallel with T016 prep if handler stable

**Phase 6–7**: T018–T021 all documentation — parallel

**Phase 8**: T022 parallel with T23 prep

### Parallel Example: User Story 1

```bash
# After T004–T007 complete, launch tests together:
Task T008: tests/test_message_handler.py
Task T009: tests/test_local_run.py

# Then sequentially:
Task T010: local_run.py CLI
Task T011: wire handler + env validation
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (handler extraction + main refactor)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `python local_run.py --text "Lunch 1200 yen"` with only `GEMINI_API_KEY`
5. Demo locally without LINE account

### Incremental Delivery

1. Setup + Foundational → shared pipeline
2. US1 → console text + image (MVP)
3. US2 → webhook server local start
4. US4 → image error handling hardened
5. US3 + US5 → integration and deploy docs
6. Polish → README + full pytest pass

### Suggested MVP Scope

**Phases 1–3 only** (T001–T011): delivers the core ask — local function testing with text/image input, simulated LINE processing, stdout reply, no LINE bot API.

---

## Notes

- Constitution test-first: plan includes tests for handler and CLI (T008, T009, T014, T015)
- `main.py` import-time exit for missing env vars must be removed in T005 before console tooling coexists cleanly
- US3 and US5 are primarily documentation; no new application code beyond README links
- Total tasks: **24** (T001–T024)
