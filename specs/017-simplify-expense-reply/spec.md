# Feature Specification: Simplify LINE expense confirmation replies

**Feature Branch**: `017-simplify-expense-reply`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: Simplify the LINE bot’s expense confirmation reply to be shorter and easier to read (receipt-style). Use an independent message-composition layer with separate sections and separators. Remove the always-visible “edit instructions” block; instead support concise help responses when users ask how-to questions. Hide category suggestions by default; allow users to correct category via natural-language category input, with a guess+confirmation step if input doesn’t exactly match a category. Default display should show category subtotals instead of per-item lines; provide a web setting to show per-item details. Visually emphasize the amount number in the reply (using LINE-supported emphasis).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receipt-style confirmation for single-item expenses (Priority: P1)

When a user submits a single expense (text or receipt), they receive a compact confirmation that includes the store/expense description (if available), the amount with visual emphasis, and the guessed category path, without long instructional text.

**Why this priority**: This is the most common path; reducing reading time directly improves daily usability.

**Independent Test**: Run the LINE bot in a test tenant/language and submit a single expense; verify the reply is short, contains the emphasized amount, and contains no long instruction paragraph.

**Acceptance Scenarios**:

1. **Given** the user is using the default setting (subtotals view) and submits a single expense, **When** the bot returns the confirmation, **Then** the reply shows a single-line/compact “receipt-style” summary and includes the amount emphasis.
2. **Given** the bot can identify a category path with confidence, **When** the confirmation is sent, **Then** the reply contains the category path once and does not include category alternatives by default.

---

### User Story 2 - Category correction via natural-language reply (Priority: P1)

After receiving a confirmation, the user replies with the desired category (in the same language they used). The system applies the category correction to the referenced expense confirmation and returns a short action summary.

**Why this priority**: The simplified UI must not break the core “reply-edit” correction flow.

**Independent Test**: Send a known expense, then reply with a category phrase; verify the change is persisted and the bot returns a short summary in the correct language.

**Acceptance Scenarios**:

1. **Given** a confirmation message and an edit reply that contains an exact/close category request, **When** the bot processes the reply, **Then** the expense category is updated and the bot acknowledges the result.
2. **Given** a user reply that does not exactly match a category name, **When** the bot guesses a category, **Then** the bot asks the user to confirm before applying the edit.
3. **Given** the user replies to an unknown/non-confirmation message, **When** the bot processes the reply, **Then** no edit is applied and the bot returns guidance that reply-to-confirmation is required.

---

### User Story 3 - Multi-item receipts default to category subtotals (Priority: P2)

For receipts with multiple items, the default confirmation shows subtotals grouped by category (instead of per-item lines). Users can optionally show per-item details via a web setting.

**Why this priority**: Most “too long” reports are caused by multi-item per-line confirmations.

**Independent Test**: Submit a multi-item receipt and verify the default reply contains category subtotals only; toggle the web setting to show per-item details and verify the expanded view appears.

**Acceptance Scenarios**:

1. **Given** multi-item expenses and default “subtotals-only” behavior, **When** the bot sends the confirmation, **Then** the reply groups totals by category and does not display per-item lines.
2. **Given** multi-item expenses and the web setting “show per-item details” enabled, **When** the bot sends the confirmation, **Then** the reply includes per-item lines in addition to subtotals.

---

### User Story 4 - How-to / help questions return concise guidance (Priority: P2)

When users send messages that ask how to edit an expense (e.g., “How do I delete?” or “How can I change the category?”), the bot responds with a short, actionable help message rather than rejecting the request.

**Why this priority**: Removing the always-visible instruction block increases reliance on on-demand help.

**Independent Test**: Send a non-expense message that is phrased as a how-to question; verify the bot returns concise help in the correct language.

**Acceptance Scenarios**:

1. **Given** a user asks a how-to question related to expense confirmations or edits, **When** the bot processes the message, **Then** it returns a short help response.
2. **Given** a user sends an unsupported non-expense request, **When** the bot processes the message, **Then** it still returns an appropriate rejection/unsupported response.

---

### Edge Cases

- **Multi-category ambiguity**: When multiple category subtotal rows are displayed and the user replies with a desired category but doesn’t indicate which subtotal row they mean, the bot must ask which row to apply the edit to.
- **Low-confidence category guess**: If the system cannot confidently map the user’s category input, it must ask for confirmation (and must not apply the edit without confirmation).
- **Language handling**: If the user language is unclear, the bot must fall back to a default language and keep responses consistent with the user’s chosen/guessed language.
- **Budget/pacing warning coexistence**: If a pacing/budget warning is applicable, it must appear as a distinct short section and must not make the confirmation unreadable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate expense confirmation replies with a receipt-style, compact layout as the default for LINE users.
- **FR-002**: System MUST construct the confirmation reply from independent message sections (e.g., pacing warning section, confirmation summary section, optional expanded detail section, help/footer section) that can be separated by visible delimiters.
- **FR-003**: System MUST visually emphasize the amount number in the reply using LINE-supported emphasis (e.g., bold-like formatting or equivalent supported styling).
- **FR-004**: System MUST, by default, display category subtotals for multi-item receipts instead of listing each individual item line.
- **FR-005**: System MUST provide a web setting that lets users enable per-item detail display in the confirmation reply.
- **FR-006**: System MUST support category correction by letting users reply with the desired category in natural language.
- **FR-007**: System MUST guess the intended category when the user’s input is not an exact category match, and MUST request confirmation before applying the edit.
- **FR-008**: System MUST disambiguate edits for multi-category confirmations when the user’s reply does not specify which displayed category subtotal row to modify.
- **FR-009**: System MUST respond to how-to/help questions about expense confirmations and edits with concise actionable guidance, instead of rejecting these requests.
- **FR-010**: System MUST preserve existing reply-edit safety constraints: edits apply only when the user’s message is a reply to a known confirmation message.
- **FR-011**: System MUST keep reply language consistent with the user’s detected/selected language (including help responses and edit summaries).

### Key Entities *(include if feature involves data)*

- **Expense Confirmation Reply**: The outbound LINE message that users reply to for edits; includes a snapshot of what was originally confirmed.
- **Category Subtotal Row**: A grouped display row representing a category and its subtotal amount for a confirmation.
- **User Display Preference**: A per-user setting (managed in the web dashboard) controlling whether confirmations show per-item details.
- **Category Guess & Confirmation State**: A transient state used when user input requires category disambiguation before applying edits.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For typical single-item confirmations, the number of lines/characters in the bot reply is reduced by at least 50% compared to the current long-form confirmation.
- **SC-002**: For typical multi-item receipts with default settings (subtotals-only), the number of lines/characters is reduced by at least 60% compared to the current per-item confirmation.
- **SC-003**: In controlled testing, at least 90% of category corrections using an exact desired category name are applied successfully without requiring a second confirmation step.
- **SC-004**: For ambiguous category inputs, the bot must never apply the category change without an explicit user confirmation.
- **SC-005**: For help/how-to questions, the first bot response contains actionable guidance that allows the user to successfully complete an edit in one additional step (≤2 messages total).
- **SC-006**: Across supported languages (ja/en/zh), the bot responds with consistent language and does not regress the ability to reply-edit confirmed expenses.

## Assumptions

- The system already has a reliable way to detect whether an inbound message is a reply to a known expense confirmation message.
- The category taxonomy used for editing exists and can map user input to category candidates.
- A web dashboard can manage a per-user (or per-tenant) toggle controlling whether confirmations show per-item details.
- When per-item details are hidden, edit targeting is based on the displayed category subtotal rows; if the user doesn’t specify, the bot asks a short disambiguation question.
