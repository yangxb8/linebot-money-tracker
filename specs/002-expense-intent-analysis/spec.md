# Feature Specification: Expense Intent Analysis

**Feature Branch**: `[002-expense-intent-analysis]`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "Add a new spec to enhance the bot so that it can analyze user input first. And only allow user request to log an expense to be processed (but we will allow more request type in future). User can only send expense via text or a picture, the agent should analyze and return the detected expense in text. If there are multiple expenses (ex. items in a receipt photo), list them separately."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Detect expense intent from text (Priority: P1)

A user sends a text message describing an expense and the bot analyzes the input before taking action.

**Why this priority**: This is the core value of the feature because accurate intent detection for text expense requests is the primary way users will submit expenses.

**Independent Test**: Send a text message containing an expense description and verify that the bot responds with a parsed expense summary rather than a generic reply.

**Acceptance Scenarios**:

1. **Given** the user sends a text message like "Log lunch expense 120 THB at cafe", **when** the bot receives the text, **then** it identifies the message as an expense logging request and responds with the detected expense details in text.
2. **Given** the user sends a text message that is not an expense request, **when** the bot analyzes the message, **then** it replies that only expense logging requests are currently supported and instructs the user how to submit expense details by text or image.

---

### User Story 2 - Detect expense details from a receipt image (Priority: P2)

A user sends a photo of a receipt or expense document and the bot extracts expense details from the image.

**Why this priority**: Support for image-based expense input is important for convenience and matches the request to accept expense submissions via picture.

**Independent Test**: Send a receipt image and verify that the bot returns a text summary of the expenses detected in the photo.

**Acceptance Scenarios**:

1. **Given** the user uploads a receipt photo containing one expense, **when** the bot processes the image, **then** it returns the detected expense detail in text.
2. **Given** the user uploads a receipt photo containing multiple expense lines, **when** the bot processes the image, **then** it returns each detected expense item separately in the response.

---

### User Story 3 - Reject unsupported request types (Priority: P3)

A user sends a non-expense request and the bot must not process it as an expense.

**Why this priority**: Preventing incorrect processing preserves trust and keeps the feature focused on expense logging only.

**Independent Test**: Send a non-expense message and verify that the bot clearly explains that only expense logging requests are supported at this time.

**Acceptance Scenarios**:

1. **Given** the user asks a general question or sends an unrelated instruction, **when** the bot analyzes the input, **then** it replies with a fixed message that only expense logging requests are supported and suggests sending the expense via text or picture.

---

### Edge Cases

- A receipt image contains text but no clear expense amounts: reply with a request for clearer expense details.
- A text message is ambiguous between expense and non-expense: the bot should clarify that only explicit expense logging is supported.
- A receipt image contains multiple items: the response must list each item separately.
- The input includes different currencies or amounts: preserve the original context in the returned expense text.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The system MUST determine whether a user message is an expense logging request before processing it.
- **FR-002**: The system MUST only process requests that are recognized as expense logging requests.
- **FR-003**: The system MUST accept expense input submitted as free-form text or as a receipt image.
- **FR-004**: The system MUST return detected expense details in plain text.
- **FR-005**: When multiple expenses are detected in one input, the system MUST list each expense item separately.
- **FR-006**: The system MUST reject non-expense requests with a clear message explaining that only expense logging is supported at this time.
- **FR-007**: The system MUST ask for clarification when the input is ambiguous or does not clearly contain expense data.
- **FR-008**: The system MUST preserve original amounts and currency context when summarizing detected expenses.
- **FR-009**: The system MUST reply with a fixed canned message for unsupported or non-expense requests to avoid unnecessary AI usage.

### Key Entities _(include if feature involves data)_

- **Expense Intent**: A user request that intends to log one or more expenses.
- **Expense Item**: A detected expense entry with amount, description, and optionally currency or merchant context.
- **Expense Summary**: The text output returned to the user that describes the detected expense(s).

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Valid expense logging requests submitted as text or image are detected and responded to with parsed expense details in the first reply.
- **SC-002**: When a single receipt contains multiple expenses, each detected item appears separately in the bot response.
- **SC-003**: Non-expense messages are declined with a clear explanation of current support limits.
- **SC-004**: Valid expense submissions do not require additional clarification in more than one follow-up message.

## Assumptions

- The current bot will only process expense logging requests for this feature; other request types are excluded from scope.
- Expense extraction is handled by the agent and returned as text rather than immediately creating a stored transaction record.
- Receipt images will be interpreted as expense data sources; OCR or extraction accuracy may vary but should still produce a best-effort itemized text result.
- Future request types such as budgeting help or analytics are out of scope for this iteration.
