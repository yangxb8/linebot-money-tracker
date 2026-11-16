# Feature Specification: Voice Expense Input

**Feature Branch**: `022-voice-expense-input`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "Add a voice input feature for line bot. User can send audio to log a expense. Limit reasonable file size and length to prevent abuse"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log an expense by voice message (Priority: P1)

A user records a short voice message in LINE describing a purchase (for example, “Lunch at the cafe, twelve hundred yen”) and sends it to the bot. The bot understands the spoken content, extracts expense details the same way it would for an equivalent text message, and replies with the usual expense confirmation. The user can then use existing reply-edit or cancel flows if something is wrong.

**Why this priority**: Hands-free expense capture is the core value of this feature; without successful voice → expense logging, nothing else matters.

**Independent Test**: Send a clear voice message that states merchant/description and amount; confirm the bot returns a normal expense confirmation and that an expense is persisted for the conversation’s ledger when persistence is enabled.

**Acceptance Scenarios**:

1. **Given** a user sends a voice message that clearly describes one expense (description/merchant and amount), **When** the bot processes it, **Then** it replies with the same style of expense confirmation used for text logging (items, amounts, categories as applicable) and does not require the user to retype the expense.
2. **Given** a voice message describes multiple distinct expenses, **When** the bot processes it, **Then** each expense is listed separately in the confirmation, consistent with multi-item text behavior.
3. **Given** a successful voice expense confirmation was sent, **When** the user replies to that confirmation to edit or cancel using existing text flows, **Then** those flows work as they do for text-originated expenses.
4. **Given** the conversation is a group/shared ledger, **When** a member logs an expense by voice, **Then** the expense is attributed to that shared ledger (same tenant rules as text/image).

---

### User Story 2 - Reject oversized or overly long audio (Priority: P1)

To prevent abuse and runaway processing cost, the bot enforces clear limits on voice message **file size** and **duration**. Messages that exceed either limit are rejected with a short, actionable reply; no expense is logged and expensive analysis is not performed.

**Why this priority**: Abuse limits were explicitly required and protect reliability for all users.

**Independent Test**: Submit (or simulate) audio above the size limit and above the duration limit; confirm rejection replies, no expense rows, and that within-limit audio still succeeds.

**Acceptance Scenarios**:

1. **Given** a voice message whose file size exceeds the configured maximum, **When** the bot receives it, **Then** it replies that the recording is too large, does not log an expense, and does not run full speech understanding.
2. **Given** a voice message whose duration exceeds the configured maximum, **When** the bot receives it, **Then** it replies that the recording is too long, does not log an expense, and does not run full speech understanding.
3. **Given** a voice message within both size and duration limits, **When** the bot receives it, **Then** processing proceeds (subject to other validation such as intelligibility and expense intent).
4. **Given** a rejection for size or length, **When** the user reads the reply, **Then** it states the limit in plain language (for example, maximum seconds and/or maximum size) and suggests sending a shorter recording or using text instead.

---

### User Story 3 - Handle unclear, empty, or non-expense voice (Priority: P2)

Not every voice message is a usable expense. The bot must fail gracefully when audio is silent, unintelligible, not an expense request, or cannot yield enough detail to log.

**Why this priority**: Poor failure UX would make voice feel unreliable even when the happy path works.

**Independent Test**: Send silent/near-silent audio, garbled audio, and a clear non-expense utterance; confirm helpful replies and no spurious expenses.

**Acceptance Scenarios**:

1. **Given** a voice message with no usable speech (silent, too quiet, or empty after decoding), **When** the bot processes it, **Then** it asks the user to try again or send text, and logs no expense.
2. **Given** speech is heard but expense details cannot be determined (missing amount, nonsense, or not an expense), **When** the bot processes it, **Then** it replies with a clear failure or “not an expense” style message consistent with text handling, and logs no expense.
3. **Given** speech indicates not-yet-purchased / wish-list intent with enough detail, **When** the bot processes it, **Then** it follows the existing wish-list propose-and-confirm path rather than logging an expense (parity with text wish intent).
4. **Given** processing fails for a transient reason after the audio was accepted, **When** the bot replies, **Then** the user gets a recoverable error message and no partial/incorrect expense is persisted.

---

### User Story 4 - Local/dev harness can exercise voice like text and image (Priority: P3)

Developers and automated tests need a way to feed sample audio into the bot pipeline without a live LINE client, analogous to existing text and image console harness flows.

**Why this priority**: Enables safe regression coverage without depending on production chats; not required for end-user value but required for sustainable quality.

**Independent Test**: Run the local harness with a short sample audio file that describes an expense and confirm the printed reply matches the voice expense confirmation path.

**Acceptance Scenarios**:

1. **Given** a sample audio file within limits, **When** it is submitted through the local harness, **Then** the bot produces the same class of confirmation reply as a live LINE voice message would.
2. **Given** a sample audio file that exceeds size or duration limits, **When** it is submitted through the local harness, **Then** the harness shows the rejection reply used for over-limit audio.

---

### Edge Cases

- Voice message exactly at the maximum duration or size is accepted; one unit over either limit is rejected.
- Very short clips (e.g. under one second) with no speech are treated as empty/unusable, not as successful zero-expense logs.
- Corrupted or undecodable audio is rejected with a retry/text suggestion; no crash.
- Duplicate delivery of the same LINE voice message does not create duplicate expenses (same idempotency expectations as other inbound message types).
- Voice combined with unrelated concurrent text from the same user is handled as separate messages (no special multi-modal merge in v1).
- Reply-edit via a new voice message (instead of text) is out of scope for v1; users edit with text replies as today.
- Extremely noisy environments that yield wrong amounts: user relies on existing confirmation + reply-edit; the bot does not auto-commit without the normal confirmation surface.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The LINE bot MUST accept inbound voice/audio messages as a supported way to request expense logging.
- **FR-002**: After accepting a within-limit voice message, the system MUST derive expense candidate details (description/merchant, amount, date when stated, and category when applicable) and present the existing expense confirmation experience used for text expenses.
- **FR-003**: Voice-originated expenses MUST follow the same ledger/tenant rules as text and image (personal vs group/shared ledger).
- **FR-004**: The system MUST enforce a maximum audio **duration** of **60 seconds**. Audio longer than this MUST be rejected before full speech understanding.
- **FR-005**: The system MUST enforce a maximum audio **file size** of **5 MB**. Audio larger than this MUST be rejected before full speech understanding.
- **FR-006**: Over-limit rejections MUST return a user-visible message that names the violated limit (duration and/or size) and suggests a shorter recording or text input; no expense MUST be created.
- **FR-007**: Unusable audio (silent, undecodable, or unintelligible) MUST produce a clear retry/text guidance reply and MUST NOT create expenses.
- **FR-008**: Non-expense speech MUST be handled consistently with non-expense text (including wish-list intent when clearly present); ordinary chat that is not an expense MUST NOT create expenses.
- **FR-009**: Existing reply-edit and cancel flows that operate on bot confirmation messages MUST work for expenses that originated from voice (edit/cancel input remains text in v1).
- **FR-010**: Voice processing MUST honor the tenant’s configured reply language, persona, and emoji settings for all user-facing bot replies on this path.
- **FR-011**: Automated functional coverage MUST include at least: successful voice expense confirmation, over-duration rejection, over-size rejection, and unusable/non-expense audio (mocked external speech/understanding services; no live production ledger mutation).
- **FR-012**: A local development harness path MUST accept an audio file input for voice expense flows, parallel to existing text/image harness usage.

### Key Entities

- **Voice expense request**: An inbound user audio message intended to describe one or more expenses; carries audio payload metadata (size, duration) and conversation/ledger context.
- **Abuse limits**: Product rules capping maximum duration (60 seconds) and maximum file size (5 MB) for accepted voice messages.
- **Expense confirmation**: The existing bot reply that lists extracted expense items for user review, edit, or cancel — shared with text/image origins.
- **Expense record**: The persisted ledger entry created after successful understanding and the product’s normal persistence rules; indistinguishable in meaning from a text-logged expense of the same content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In manual or harness trials with clear speech stating description and amount, users receive a correct expense confirmation on the **first attempt** for at least **90%** of within-limit samples.
- **SC-002**: Over-limit audio (duration or size) is rejected with a clear message and **0** expenses created in **100%** of trials.
- **SC-003**: End-to-end voice expense confirmation for a typical short clip (under 15 seconds) completes within **10 seconds** of message receipt under normal conditions (user-perceived wait, not internal SLA jargon).
- **SC-004**: Users can correct a mis-heard amount via the existing reply-edit flow without re-recording, in a single reply, for confirmed voice-originated expenses.
- **SC-005**: Automated functional tests for the voice happy path and both abuse-limit rejections remain green in the project’s PR verification suite.

## Assumptions

- “Voice input” means LINE **voice/audio messages** (user holds-to-talk or sends an audio file that LINE delivers as an audio message), not phone calls or third-party voice assistants.
- v1 focuses on **expense logging** (and wish-list intent parity when speech clearly matches existing wish phrases); other bot capabilities via voice are out of scope.
- **60 seconds** and **5 MB** are the v1 abuse caps; they can be tuned later without changing the product concept.
- Duration is measured from the audio content (or reliable provider metadata); if duration cannot be determined, the system still enforces the size limit and may reject undecodable audio.
- Speech understanding quality is “good enough” for short expense utterances in the languages the bot already supports for text (Japanese, English, Chinese); perfect transcription of long narratives is not required.
- Reply-edit and cancel remain **text replies** to the confirmation message in v1; voice-to-edit is deferred.
- Web dashboard does not gain a microphone capture UI in this feature.
- Voice messages consume the same usage/quota posture as other AI-assisted inbound messages where metering already exists; no separate unlimited voice tier.
- Existing confirmation UX, category memory, budgets, and persona/i18n behavior are reused rather than inventing a parallel voice-only confirmation format.

## Out of Scope

- Real-time streaming transcription while the user is still speaking
- Voice-based reply-edit, category change, or cancel commands (text replies only in v1)
- Web or LIFF microphone expense entry
- Storing raw audio long-term as a user-facing recording library
- Speaker identification / multi-speaker separation beyond ordinary single-user LINE messages
- Custom per-tenant abuse limits in v1 (global product defaults only)
- Support for arbitrary large media types that are not ordinary LINE voice/audio messages
