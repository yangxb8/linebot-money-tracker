# Feature Specification: Expense Reply Edits

**Feature Branch**: `005-expense-reply-edits`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "After logging an expense for user and ask for their confirmation, Line user can reply to the message to make change. User will reply to AI's message — memorize msg ID and content of our reply so we can take action. Any editable fields of an expense record, including deletion, is possible based on user reply. After taking action, LLM should reply what it has done."

## Clarifications

### Session 2026-06-08

- Q: Multi-item bare `取消`? → A: **`soft_delete_all`** with YES confirmation (not “which item?”).
- Q: `全部取消` / `全部删除` / `取消全部`? → A: **`soft_delete_all`**; user confirms with YES/`是` on the **bot confirmation message** (reply-to-message).
- Q: `取消` while delete-all pending? → A: **`cancel_pending`** (abort bulk delete).

### Session 2026-06-06

- Q: When a user deletes an expense via reply, should the record be permanently removed or soft-deleted? → A: **Soft delete** — mark as deleted, exclude from totals/analysis, retain row for audit; user can **cancel/undo a deletion** by replying to the same confirmation (e.g., "undo delete", "restore").
- Q: On multi-item confirmations, what does a bare numbered reply (`1`–`3`) mean? → A: **Single item:** bare `1`–`3` selects category alternative. **Multi-item:** user must identify the target item (description, amount, or ordinal); bare number alone → bot asks which item before applying the category pick.
- Q: When user says "delete all" on a multi-item confirmation, what happens? → A: **Confirm first** — bot asks user to confirm before soft-deleting all active linked expenses (e.g., reply YES to proceed).
- Q: Which languages are supported for edit replies and action summaries? → A: **Multilingual** — accept Japanese, English, and Chinese edit replies; bot action summary matches the language of the user's reply.
- Q: Can user "restore all" after bulk delete on a multi-item confirmation? → A: **Supported** — "restore all" immediately restores every soft-deleted expense linked to that confirmation; bot lists each restored item (no extra confirmation step).

## Dependencies

- Requires expense logging and confirmation replies from the prior expense-storage feature (detected expenses persisted per user with category guess and confirmation prompt).
- Builds on the predefined category taxonomy and per-item expense records (including multi-item receipts).

## Out of Scope (this feature)

- Logging **new** expenses via a reply (only edit or delete expenses linked to the bot message being replied to)
- Editing expenses by referencing a message other than the specific bot confirmation being replied to
- User-created or custom category trees (taxonomy remains predefined)
- Budget setup, budget impact in replies, or spending analysis commands
- Admin or bulk edit tools outside the reply flow
- Persisting arbitrary conversation history beyond what is needed to interpret and audit reply-based edits

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Change category by replying to the confirmation message (Priority: P1)

After the bot logs one or more expenses and sends a confirmation reply (with guessed category and numbered alternatives), the user replies **to that bot message** to pick a different category — for example by sending `2` or natural language such as "category should be groceries".

**Why this priority**: Category confirmation was promised in the prior feature but not persisted; this is the most common correction users will make immediately after logging.

**Independent Test**: Log a single expense, reply to the bot's confirmation with a category change, verify the stored expense reflects the new category and the user receives a summary of what changed.

**Acceptance Scenarios**:

1. **Given** the bot logged one expense and sent a confirmation listing category alternatives numbered 1–3, **When** the user replies to that message with `2`, **Then** the expense category is updated to alternative 2 and the bot replies describing the new category path.
2. **Given** the bot logged one expense with a guessed category, **When** the user replies in natural language requesting a specific valid taxonomy category, **Then** the expense category is updated accordingly and the bot confirms the change in plain language.
3. **Given** the user replies with a category that cannot be mapped to the predefined taxonomy, **When** processing completes, **Then** no category change is applied and the bot explains that the category was not recognized and asks the user to try again.
4. **Given** the user replies to the confirmation but does not mention category, **When** no other editable intent is detected, **Then** the bot asks what the user would like to change without modifying stored data.
5. **Given** a confirmation with **multiple** expense items and the user replies with a bare number (`1`, `2`, or `3`) without identifying an item, **When** processing completes, **Then** the bot asks which line item the category alternative applies to and does not change stored data until clarified.
6. **Given** a confirmation with multiple items and the user identifies the target item (e.g., "coffee: 2" or "item 1 category 2"), **When** processing completes, **Then** only that item's category is updated to the selected alternative.

---

### User Story 2 - Edit amount, description, or date by reply (Priority: P1)

The user replies to the bot's expense confirmation to correct other fields — for example "amount was 3800 not 3500", "description should be supermarket run", or "that was yesterday".

**Why this priority**: Receipt parsing and detection errors are common; users need to fix core expense fields without re-submitting the whole receipt.

**Independent Test**: Log an expense, reply with an amount correction only, verify amount updates and other fields remain unchanged; repeat for description and expense date.

**Acceptance Scenarios**:

1. **Given** a stored expense with amount 3500, **When** the user replies "actually 3800 yen", **Then** the stored amount becomes 3800 and the bot confirms the update.
2. **Given** a stored expense, **When** the user replies with a new description, **Then** only the description field changes and the bot summarizes the new description.
3. **Given** a stored expense, **When** the user replies with a corrected expense date (relative or absolute), **Then** the expense date is updated using Japan Standard Time calendar boundaries and the bot states the new date.
4. **Given** the user replies changing multiple fields in one message (e.g., amount and category), **When** processing succeeds, **Then** all requested valid changes are applied atomically and the bot lists each change.
5. **Given** the user provides an invalid amount or date, **When** validation fails, **Then** no partial update is saved and the bot explains what was wrong.

---

### User Story 3 - Delete an expense by reply (Priority: P1)

The user decides the logged expense was wrong or duplicate and replies to the confirmation asking to remove it — for example "delete this", "cancel", or "wrong receipt".

**Why this priority**: Deletion is explicitly required and is a safety valve when detection was completely wrong.

**Independent Test**: Log an expense, reply asking to delete, verify the record is soft-deleted (excluded from totals, row retained) and the bot confirms deletion; reply again to restore and verify the expense reappears in active records.

**Acceptance Scenarios**:

1. **Given** one expense linked to the confirmation message, **When** the user replies asking to delete or cancel it, **Then** that expense is soft-deleted (hidden from analysis totals, row retained for audit) and the bot confirms it was deleted.
2. **Given** multiple expenses linked to the same confirmation message, **When** the user asks to delete without specifying which item, **Then** the bot asks which item to delete (by description/amount) before making changes.
3. **Given** the user asks to delete a specific item from a multi-item confirmation, **When** the item is identified, **Then** only that item is soft-deleted and remaining items stay unchanged.
4. **Given** multiple active expenses are linked to the confirmation and the user asks to delete all, **When** processing completes, **Then** the bot asks for explicit confirmation before soft-deleting any records and does not delete until the user confirms (e.g., replies YES).
5. **Given** the user confirmed delete-all, **When** processing completes, **Then** all active linked expenses are soft-deleted and the bot summarizes each deleted item.
6. **Given** an expense was soft-deleted via reply, **When** the user replies to the same confirmation asking to undo or restore the deletion, **Then** the expense returns to active records and the bot confirms it was restored.
7. **Given** multiple expenses were soft-deleted on the same confirmation (including via delete-all), **When** the user replies asking to restore all, **Then** all soft-deleted linked expenses are restored immediately and the bot lists each restored item.
8. **Given** all linked expenses are soft-deleted, **When** the user replies with a field edit (not restore), **Then** the bot explains there are no active expenses to edit and offers to restore if appropriate.

---

### User Story 4 - Link user replies to the correct bot message and expenses (Priority: P1)

When the bot sends a confirmation, the system remembers enough context from that outbound message (identifier and content snapshot) to recognize a later user reply as referring to those expense records.

**Why this priority**: Without durable linkage between the bot's confirmation message and stored expenses, reply-based edits cannot work reliably on LINE.

**Independent Test**: Send confirmation for message A; reply to message A and verify edits apply; reply to unrelated message B and verify no edits apply to A's expenses.

**Acceptance Scenarios**:

1. **Given** the bot sent a confirmation message for a logged expense, **When** the system stores the linkage, **Then** the outbound message identifier, user identity, timestamp, reply text snapshot, and references to all expense records from that confirmation are retrievable.
2. **Given** a user reply targets the stored confirmation message, **When** the reply is processed, **Then** only expenses linked to that confirmation are eligible for edit or delete.
3. **Given** a user sends a new expense message (not a reply), **When** processed, **Then** the normal log-and-confirm flow runs and no prior confirmation linkages are modified.
4. **Given** a user reply targets a bot message that is not a stored expense confirmation, **When** processed, **Then** the bot politely explains it cannot edit that message and does not change expense records.

---

### User Story 5 - Bot summarizes actions after each reply edit (Priority: P2)

After applying edits or deletion, the bot sends a clear follow-up message describing what changed (or that nothing changed), so the user can trust the correction worked.

**Why this priority**: Users need closure after a correction; a vague or silent success erodes trust.

**Independent Test**: Perform a category change and verify the follow-up mentions old and new category paths; perform a delete and verify the follow-up states the expense was removed.

**Acceptance Scenarios**:

1. **Given** a successful field update, **When** processing completes, **Then** the bot reply states each field changed, the previous value (when known), and the new value.
2. **Given** a successful soft deletion or restoration, **When** processing completes, **Then** the bot reply confirms which expense was deleted or restored using description and amount.
3. **Given** no changes were applied, **When** processing completes, **Then** the bot explains why (unrecognized intent, invalid value, or ambiguous multi-item request) and suggests next steps.
4. **Given** storage is temporarily unavailable during an edit, **When** processing completes, **Then** the user receives a friendly failure message and no silent partial state is implied.

---

### Edge Cases

- User replies to a confirmation long after it was sent — edits still apply if the linkage and expense records exist.
- User requests "delete all" on a multi-item confirmation — bot prompts for explicit confirmation before soft-deleting; no deletion until user confirms.
- User soft-deletes then immediately replies to restore — expense returns to active state; monthly/yearly totals include it again.
- User requests "restore all" after bulk soft-delete — all linked soft-deleted expenses restored immediately; bot lists each item.
- User requests "restore all" when no soft-deleted items remain — bot explains there is nothing to restore.
- User attempts to restore an expense that was never deleted — bot explains no deletion to undo.
- User replies in an unsupported language — bot responds in Japanese asking the user to reply in Japanese, English, or Chinese.
- User sends multiple replies in quick succession to the same confirmation — each reply is processed independently; later replies operate on current stored state.
- User mixes edit and delete intent in one message — system applies a coherent interpretation or asks for clarification before destructive action.
- User attempts to set currency to an unsupported or malformed code — change rejected with explanation.
- Confirmation covered multiple items but user says "change category to transit" without item reference — bot asks which line item unless only one active expense is linked.
- Confirmation covered multiple items and user sends bare `1`–`3` — bot asks which item the numbered category alternative applies to (single-item confirmations: bare number selects alternative directly).
- Webhook redelivery of the same user reply — duplicate edits MUST NOT be applied twice (idempotent on user reply message identity).
- Local/console testing harness — reply-based edits MAY use a simulated reply context; behavior MUST match production rules when reply linkage is provided.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist, for each expense confirmation sent to a user, the outbound message identifier, a snapshot of the confirmation text, the user identity, and references to every expense record created or summarized in that confirmation.
- **FR-002**: System MUST detect when an inbound user message is a reply to a previously stored confirmation message.
- **FR-003**: System MUST restrict edit and delete operations on expenses to the user who owns those records.
- **FR-004**: System MUST allow users to update any stored expense field via reply: description, amount, currency, expense date, and category assignment (within the predefined taxonomy).
- **FR-005**: System MUST allow users to **soft-delete** expense record(s) linked to the confirmation via reply (exclude from analysis totals, retain row for audit), with explicit handling when multiple items are present. When the user requests deletion of **all** items on a multi-item confirmation, system MUST require explicit confirmation before applying bulk soft-delete.
- **FR-005a**: System MUST allow users to **restore** (undo) a soft-deleted expense via reply to the same confirmation message, returning it to active records.
- **FR-005b**: System MUST support **restore all** — when the user requests restoration of all soft-deleted expenses linked to a confirmation, all are restored immediately without an extra confirmation step; the bot summarizes each restored item.
- **FR-006**: System MUST support category changes both by numbered alternative selection (when the confirmation listed alternatives) and by natural-language category requests mapped to the predefined taxonomy. For **single-item** confirmations, bare `1`–`3` selects the corresponding category alternative. For **multi-item** confirmations, bare numbers alone MUST NOT apply a category change until the user identifies the target item.
- **FR-007**: System MUST validate all proposed field values before persisting; invalid proposals MUST NOT partially update unrelated fields.
- **FR-008**: System MUST apply multiple valid field changes from a single user reply in one atomic update per affected expense record.
- **FR-009**: After processing a reply edit, system MUST send the user a natural-language summary of actions taken, including field-level before/after detail when a change occurred.
- **FR-010**: System MUST NOT apply edits when the inbound message is not a reply to a known confirmation, except to return guidance that reply-to-confirm is required.
- **FR-011**: System MUST treat duplicate delivery of the same user reply message as idempotent (no double application of the same edit).
- **FR-012**: System MUST continue to use Japan Standard Time for expense date interpretation and calendar boundaries when users correct dates via reply.
- **FR-013**: When category level changes (e.g., L3 to L1), system MUST update stored category assignment and hierarchy rollups consistently with existing expense storage rules.
- **FR-014**: System MUST retain auditability of reply-driven changes (at minimum: which confirmation, which user reply, and what changed) for operator troubleshooting.
- **FR-015**: System MUST accept edit, delete, restore, and confirmation replies in **Japanese, English, or Chinese**; action summaries MUST be returned in the same language as the user's reply when detectable, otherwise Japanese.

### Key Entities

- **Confirmation message record**: Represents one bot expense confirmation sent to a user — links outbound message identifier, user identity, sent timestamp, text snapshot, and one or more expense record references.
- **Expense record**: Existing persisted expense (description, amount, currency, expense date, category assignment, user identity, source message linkage, active/deleted status); subject to update, soft-delete, or restoration via reply.
- **Reply edit action**: A interpreted user intent derived from a reply (field updates and/or delete) applied against one or more linked expense records, with outcome status for user feedback.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can correct a wrongly guessed category by replying to the confirmation in under 30 seconds end-to-end (reply sent to summary received), for single-item expenses.
- **SC-002**: At least 90% of single-field correction replies (amount, description, or numbered category pick) result in the intended stored change on first attempt in user acceptance testing.
- **SC-003**: 100% of successful edit or delete operations produce a bot follow-up that explicitly states what changed or that deletion occurred (no silent success).
- **SC-004**: Zero cross-user edits in testing — a user cannot modify another user's expenses via reply linkage.
- **SC-005**: Duplicate platform redelivery of the same user reply does not produce duplicate mutations in 100% of tested retry scenarios.
- **SC-006**: Multi-item confirmations where the user specifies the target item support correct per-item edits in at least 85% of structured test cases.

## Assumptions

- Users interact via LINE (or equivalent messaging platform) using native **reply-to-message** threading so the platform provides the identifier of the message being replied to.
- Expense logging, taxonomy, and persistence from the prior feature are already in production.
- Numbered alternatives in the confirmation (1–3) map directly to the alternative categories shown in that specific confirmation text snapshot. On single-item confirmations, bare `1`–`3` selects the alternative; on multi-item confirmations, the user must identify which item before a numbered category pick is applied.
- Natural-language understanding is used to interpret free-text replies into structured edit intents; unrecognized intents result in clarification, not silent failure. Supported reply languages: **Japanese, English, and Chinese**; bot summaries match the user's reply language when detectable.
- Deletion is **soft delete** — expenses are marked deleted and excluded from monthly/yearly totals and analysis; rows are retained for audit. Users can restore a soft-deleted expense by replying to the same confirmation, or restore all soft-deleted items on that confirmation in one action.
- Only expenses associated with the replied-to confirmation are in scope; users cannot edit historical expenses by replying to unrelated old messages unless those messages are stored confirmation records.
- Console/local harness may simulate reply context for automated tests; production behavior is authoritative for acceptance.
