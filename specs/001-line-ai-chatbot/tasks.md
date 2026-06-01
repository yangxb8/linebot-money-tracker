# Tasks: LINE AI Chatbot

**Input**: Design documents from `/specs/001-line-ai-chatbot/`

**Prerequisites**: plan.md, spec.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency configuration, and test scaffolding

- [ ] T001 [P] Add Gemini API integration dependency to `requirements.txt`
- [ ] T002 [P] Create `tests/` directory and base test file at `tests/test_line_webhook.py`
- [ ] T003 [P] Add environment variable validation for `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `GEMINI_API_KEY`, and `GEMINI_API_URL` in `main.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the core service components required before user stories can be implemented

- [ ] T004 [P] Create `services/gemini_client.py` for Gemini request/response handling
- [ ] T005 [P] Create `services/line_event.py` to parse LINE webhook events and map text messages
- [ ] T006 [P] Add structured logging setup in `main.py` for webhook processing and AI service calls
- [ ] T007 Implement Gemini API error, timeout, and fallback handling in `services/gemini_client.py`
- [ ] T008 Add LINE webhook signature validation and unsupported-event fallback behavior in `main.py`

---

## Phase 3: User Story 1 - Chat reply flow (Priority: P1)

**Goal**: Accept LINE text messages, send user text to Gemini, and reply with generated results.

**Independent Test**: A valid LINE text webhook returns a Gemini-generated reply.

- [ ] T009 [P] [US1] Implement Gemini request creation in `services/gemini_client.py`
- [ ] T010 [US1] Implement LINE text message forwarding and reply flow in `main.py`
- [ ] T011 [P] [US1] Add an end-to-end webhook test for a valid LINE text event in `tests/test_line_webhook.py`

---

## Phase 4: User Story 2 - Input validation and fallback handling (Priority: P2)

**Goal**: Ensure invalid or unsupported input is handled gracefully and the bot does not crash.

**Independent Test**: An unsupported or empty event returns a clear fallback message.

- [ ] T012 [US2] Add validation for empty or non-text LINE events in `main.py`
- [ ] T013 [US2] Add user-friendly fallback messaging for Gemini failures in `services/gemini_client.py`
- [ ] T014 [P] [US2] Add tests for unsupported LINE events and Gemini failure fallback in `tests/test_line_webhook.py`

---

## Phase 5: User Story 3 - Developer feedback and tracing (Priority: P3)

**Goal**: Provide observability for LINE webhook processing and Gemini API interactions.

**Independent Test**: Logs contain webhook event metadata and Gemini response status.

- [ ] T015 [US3] Add request and response logging for LINE events in `main.py`
- [ ] T016 [US3] Add Gemini API call logging and status tracing in `services/gemini_client.py`
- [ ] T017 [P] [US3] Add log assertions or trace validation to `tests/test_line_webhook.py`

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Document deployment and ensure the sample bot is cloud-ready.

- [ ] T018 [P] Document required environment variables and deployment steps in `README.md`
- [ ] T019 [P] Add cloud deployment guidance for LINE webhook hosting in `README.md`
- [ ] T020 [P] Review new code and tests for style, readability, and adherence to the project constitution

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: No dependencies, can start immediately
- **Phase 2**: Depends on Phase 1 completion
- **User Stories**: Depend on Phase 2 completion
- **Polish**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Delivers MVP chat reply flow and is the top priority
- **User Story 2 (P2)**: Adds validation and fallback behavior, can proceed after foundation
- **User Story 3 (P3)**: Adds observability and trace diagnostics, can be implemented after foundation

### Parallel Opportunities

- Setup tasks `T001`, `T002`, and `T003` can run in parallel
- Foundational tasks `T004`, `T005`, and `T006` can run in parallel
- Implementation tasks for each story can be worked on in parallel after Phase 2
- Documentation and cleanup tasks `T018`, `T019`, and `T020` can be parallelized

## Implementation Strategy

### MVP First

1. Complete Phase 1 setup tasks
2. Complete Phase 2 foundation tasks
3. Complete User Story 1 tasks (`T009`, `T010`, `T011`)
4. Validate the chat reply flow independently

### Incremental Delivery

1. Add User Story 2 handling and validation
2. Add User Story 3 logging and traceability
3. Finalize documentation and cloud deployment notes
