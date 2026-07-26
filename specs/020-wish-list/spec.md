# Feature Specification: Wish List

**Feature Branch**: `020-wish-list`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "wish list feature across web app and line bot. - in web app a new page to maintain wish list, it’s a list with item name and price, and category, and optional link the tenant wants to buy. The list can be ordered to show priority, it can also be sorted automatically by created time and price. The list can be crud by user. - wish list can be executed and add to expense, ask user to confirm and they can change all fields in wish list. Once executed they will disappear from wish list but add a button to filter for executed wish list so user can see them. In expense card, other than category also shows tag for wish list item. - in line bot, user can add wish list item. They send a normal expense message or item image, but in text they need to indicate it’s not brought yet. Such as “I want to buy” etc. after receiving such request, bot can reply with budget impact of this purchase, and ask user if they want to add to wish list. User can then confirm to add"

## Clarifications

### Session 2026-07-26

- Q: When the LINE bot proposes a wish list add, can the user edit extracted fields before confirming, or is confirmation yes/no only? → A: Yes/no confirm only; post-add edits are web-only
- Q: When executing a wish list item into an expense, what is the expense date? → A: Default to today; user can change the date on the execute confirmation form
- Q: In the executed wish list filter, which values should each item show? → A: Final expense values only (what was confirmed at execute), plus link to the expense
- Q: Where can users execute a wish list item into an expense? → A: Web only (LINE bot can add to wish list, but not execute)
- Q: What should the LINE bot’s budget impact reply include when proposing a wish list add? → A: Both remaining budget and pace note when ahead of schedule; remaining-only when on/under pace

## Dependencies

- Reuses existing tenant/ledger access (personal and group ledgers) and signed-in web dashboard access control.
- Reuses the existing expense category hierarchy for assigning categories to wish list items and resulting expenses.
- Reuses monthly budget configuration and budget-vs-spending calculations when presenting purchase budget impact in the LINE bot flow.
- Reuses existing expense logging semantics so that executing a wish list item creates a normal expense that counts toward budgets and appears in expense history.

## Out of Scope (this feature)

- Public or shareable wish lists outside the tenant’s ledgers
- Price-drop monitoring, affiliate checkout, or purchasing from external stores
- Multi-currency wish list amounts (JPY only, consistent with the rest of the product)
- Automatic conversion of every non-expense “want” message without an explicit not-yet-purchased intent
- Editing or managing wish list items from the LINE bot beyond the add-with-confirmation flow (full CRUD remains on the web page)
- Executing a wish list item (converting it to an expense) from the LINE bot — execute is web-only in v1
- Undoing an execution (restoring an executed item back to the active wish list) in v1
- Separate wish list budgets distinct from existing monthly budgets
- Notifications or reminders that a wish list item has been sitting too long

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintain an active wish list in the web app (Priority: P1)

A signed-in user opens a new **Wish List** page for the active personal or group ledger. They can create, view, edit, and delete wish list items. Each item has a name, price, category, and an optional product link. By default the list shows only active (not-yet-purchased) items in the user’s manual priority order. The user can drag or otherwise reorder items to reflect purchase priority, and can also switch to automatic sorting by created time or by price.

**Why this priority**: Without a maintainable list, neither purchase planning nor execution can deliver value.

**Independent Test**: Create three items with different prices and categories, reorder them manually, switch sort to price and confirm order changes, edit one item’s name and link, delete another, and reload to confirm persistence for the active ledger only.

**Acceptance Scenarios**:

1. **Given** a signed-in user on a ledger with no wish list items, **When** they open the Wish List page, **Then** they see an empty active list and can add a new item with name, price, category, and optional link.
2. **Given** a user enters a new item with valid name, price, and category, **When** they save, **Then** the item appears in the active list for that ledger and is assigned a position at the end of the current priority order (unless the user placed it otherwise).
3. **Given** multiple active items, **When** the user reorders them by priority, **Then** the new order is saved and shown as the default active list order on reload.
4. **Given** multiple active items, **When** the user sorts by created time, **Then** items are ordered by when they were added (newest first).
5. **Given** multiple active items, **When** the user sorts by price, **Then** items are ordered by price (highest first), with a clear control to reverse to lowest first if offered.
6. **Given** an existing item, **When** the user edits any of name, price, category, or link and saves, **Then** the updated values are shown immediately and persist after reload.
7. **Given** an existing active item, **When** the user deletes it, **Then** it is removed from the active list and no longer available to execute.
8. **Given** invalid input (missing name, non-numeric or negative price, missing category), **When** the user attempts to save, **Then** validation errors are shown and nothing is saved.
9. **Given** the user switches from personal to group ledger (or vice versa), **When** the Wish List page loads, **Then** it shows that ledger’s independent wish list, not the other ledger’s.

---

### User Story 2 - Execute a wish list item into an expense (Priority: P1)

When the user is ready to buy an active wish list item **on the web Wish List page**, they choose **Execute** (or equivalent). The system asks them to confirm and presents an editable form pre-filled from the wish list item (name/description, amount, category, and any other fields that map to an expense). The **expense date defaults to today** and is editable on this form. The user may change any of those fields before confirming. On confirm, the system creates an expense from the confirmed values, marks the wish list item as executed, and removes it from the default active list. The LINE bot does not offer execute in v1.

**Why this priority**: Turning planned purchases into real expenses is the main payoff of keeping a wish list.

**Independent Test**: Create a wish list item, execute it while changing the amount and category on the confirmation form, confirm the new expense appears in expense history with the adjusted values, and confirm the item no longer appears in the active wish list.

**Acceptance Scenarios**:

1. **Given** an active wish list item, **When** the user starts execution, **Then** they see a confirmation step with all mapped fields editable and pre-filled from the item, and the expense date defaulted to today.
2. **Given** the confirmation form, **When** the user changes name, amount, category, and/or date and confirms, **Then** the created expense reflects the confirmed values (not necessarily the original wish list values or today’s date).
3. **Given** the user confirms execution without changing the date, **When** the flow completes, **Then** the expense is dated today.
4. **Given** the user confirms execution, **When** the flow completes, **Then** a normal expense exists in the ledger and the wish list item is no longer shown in the default active list.
5. **Given** the user cancels the confirmation, **When** they return to the list, **Then** the item remains active and unchanged, and no expense was created.
6. **Given** execution succeeds, **When** the user views expense history, **Then** the new expense is visible like any other expense for that ledger.

---

### User Story 3 - Add a wish list item from the LINE bot with budget impact (Priority: P1)

A user sends a LINE message that looks like a normal expense (text and/or item/receipt image) but the text indicates the item has **not been purchased yet** (for example, “I want to buy”, “買いたい”, “wishlist”, or similar intent). The bot does **not** log an expense. Instead it extracts candidate item details (name, price, category when possible), replies with the **budget impact** of making that purchase (using the ledger’s existing monthly budgets when applicable), and asks whether to add the item to the wish list (**yes/no only** — no in-chat field editing). The user confirms to add; on confirmation the item appears in that ledger’s active wish list. Any corrections to name, price, category, or link are done afterward on the web Wish List page.

**Why this priority**: Capturing purchase intent at the moment it happens in chat is a primary acquisition path for wish list items.

**Independent Test**: Send “I want to buy headphones 15000 yen” in a ledger with a matching budget, confirm the bot replies with budget impact and an add prompt (no expense created), confirm the add, and verify the item appears on the web Wish List page.

**Acceptance Scenarios**:

1. **Given** a user sends a text message with clear not-yet-purchased intent and enough detail to extract name and price, **When** the bot processes it, **Then** it does not create an expense and instead replies with extracted details, budget impact, and a prompt to add to the wish list.
2. **Given** a user sends an item/receipt image plus text indicating not-yet-purchased intent, **When** the bot processes it, **Then** it treats the request as wish list intent (not expense logging) and follows the same budget-impact + confirm-to-add flow.
3. **Given** an applicable monthly budget exists and the hypothetical purchase would leave spending on or under pace, **When** the bot replies, **Then** the budget impact states remaining budget now and remaining if the purchase were made (no pace warning).
4. **Given** an applicable monthly budget exists and the hypothetical purchase would put spending ahead of schedule, **When** the bot replies, **Then** the budget impact includes remaining-budget figures **and** a pace note that the purchase would put spending ahead of schedule.
5. **Given** no applicable budget is configured, **When** the bot replies, **Then** it still shows the candidate item details and asks to add to the wish list, stating that no budget limit applies (or equivalent clear “unlimited / no budget set” messaging).
6. **Given** the bot asked to add to the wish list, **When** the user confirms (yes), **Then** an active wish list item is created on the conversation’s ledger using the bot’s offered extracted details (no in-chat edits).
7. **Given** the bot asked to add to the wish list, **When** the user declines (no) or ignores without confirming, **Then** no wish list item is created and no expense is logged.
8. **Given** a wish list item was added via bot with imperfect extracted details, **When** the user opens the web Wish List page, **Then** they can edit name, price, category, and link there.
9. **Given** a message that is a normal expense without not-yet-purchased intent, **When** the bot processes it, **Then** existing expense logging behavior is unchanged (this feature must not intercept ordinary expenses).
10. **Given** a group chat / group ledger context, **When** a wish list add is confirmed, **Then** the item is stored on the **group** ledger’s wish list, not the sender’s personal ledger.

---

### User Story 4 - Review executed wish list items (Priority: P2)

After items are executed, they no longer clutter the active list. The user can switch a filter (or equivalent control) to view executed wish list items for historical reference. Each executed row shows the **final expense values** (what was confirmed at execute) and a clear way to open/view the related expense — not a separate snapshot of the pre-execute planned values.

**Why this priority**: Users need a way to audit past planned purchases without mixing them into the active priority list.

**Independent Test**: Execute an item while changing amount and category on confirm, confirm the active list hides it, turn on the executed filter, and verify the row shows the confirmed expense values and links to that expense.

**Acceptance Scenarios**:

1. **Given** one or more executed items exist, **When** the user views the default Wish List page, **Then** only active items are shown.
2. **Given** executed items exist, **When** the user enables the executed filter, **Then** executed items are listed and clearly marked as executed (and are not editable as active priority items).
3. **Given** an item was executed with fields changed on the confirm form, **When** it appears in the executed filter, **Then** the row shows the confirmed expense values (not the pre-execute wish list values) and provides access to the related expense.
4. **Given** no executed items exist, **When** the user enables the executed filter, **Then** they see an empty executed state rather than active items.

---

### User Story 5 - Wish list tag on expense cards (Priority: P2)

When an expense was created by executing a wish list item, expense cards in the web app show a **wish list** tag in addition to the category, so users can distinguish planned-then-purchased spending from ad-hoc expenses.

**Why this priority**: Visibility of which expenses came from the wish list reinforces the planning loop and aids review.

**Independent Test**: Execute a wish list item, open the expenses view, and confirm the resulting expense card shows both its category and a wish list tag; confirm a manually logged expense without wish list origin shows no such tag.

**Acceptance Scenarios**:

1. **Given** an expense created via wish list execution, **When** the user views that expense’s card, **Then** they see the category and a distinct wish list tag/label.
2. **Given** an expense created through normal bot or web logging (not from wish list execution), **When** the user views that expense’s card, **Then** no wish list tag appears.
3. **Given** a wish-list-origin expense whose category was changed during execution confirmation, **When** the card is shown, **Then** it shows the confirmed category and still shows the wish list tag.

---

### Edge Cases

- What happens when the user tries to execute an item that was already executed or deleted by another session? The system refuses with a clear message and refreshes the list.
- What happens when wish list intent is detected but price cannot be determined? The bot asks for the missing price (or enough detail) before offering budget impact and add confirmation; it still does not log an expense.
- What happens when wish list intent is detected but category cannot be inferred? The bot may proceed with a suggested or “uncategorized / needs category” state consistent with existing expense categorization fallbacks, and still offer add-to-wish-list after stating budget impact using the best available level (including total-only or no-budget messaging).
- What happens when the optional product link is malformed? The web form validates URL format and blocks save until corrected or cleared.
- What happens when sorting by price with equal prices? Ordering is stable (tie-break by priority order or created time) so the list does not jump randomly on refresh.
- How does the system treat messages that both look like a completed purchase and contain weak “want” wording? Only clear not-yet-purchased intent routes to wish list; ambiguous cases follow ordinary expense flow (documented in Assumptions).
- What happens in a group ledger when a member deletes or executes an item another member added? Any member with access to that ledger can manage its shared wish list; the change is reflected for all members.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The web app MUST provide a Wish List page scoped to the currently selected ledger (personal or group).
- **FR-002**: Users MUST be able to create, read, update, and delete active wish list items on that page.
- **FR-003**: Each wish list item MUST support: name, price, category (from the ledger’s existing categories), and an optional product link.
- **FR-004**: The active list MUST support manual priority ordering that persists for the ledger.
- **FR-005**: Users MUST be able to sort the active list automatically by created time and by price (in addition to the manual priority order view).
- **FR-006**: The default Wish List view MUST show only active (not-yet-executed) items in manual priority order.
- **FR-007**: Users MUST be able to start an execute flow **from the web Wish List page** on an active item that opens a confirmation step with all expense-mapped fields editable and pre-filled from the item, including an expense date that defaults to today and is editable before confirm. The LINE bot MUST NOT provide an execute / convert-to-expense action in v1.
- **FR-008**: On confirmed execution, the system MUST create a normal expense from the confirmed field values (including the confirmed date), mark the wish list item as executed, and hide it from the default active list.
- **FR-009**: Canceling the execute confirmation MUST leave the wish list item active and MUST NOT create an expense.
- **FR-010**: Users MUST be able to filter the Wish List page to view executed items; each executed row MUST present the final expense values from execution and a way to open/view the related expense (not a separate pre-execute planned snapshot).
- **FR-011**: Expense cards for expenses created via wish list execution MUST show a wish list tag in addition to category; other expenses MUST NOT show that tag.
- **FR-012**: The LINE bot MUST detect not-yet-purchased intent in user messages (text alone, or image plus text) that would otherwise resemble expense logging.
- **FR-013**: When wish list intent is detected, the bot MUST NOT create an expense; it MUST present candidate item details, budget impact of the potential purchase, and ask the user to confirm adding to the wish list.
- **FR-014**: Budget impact messaging MUST use the ledger’s existing monthly budget rules when a relevant budget exists: always include remaining budget now and remaining if the purchase were made; include a pace note only when the hypothetical purchase would put spending ahead of schedule; and MUST clearly indicate when no budget applies.
- **FR-015**: On user confirmation (yes) in the bot flow, the system MUST create an active wish list item on the conversation’s ledger using the offered extracted details; the bot MUST NOT support editing those fields in chat before or during confirmation (edits are web-only after add).
- **FR-016**: Ordinary expense messages without not-yet-purchased intent MUST continue to follow existing expense logging behavior unchanged.
- **FR-017**: Wish list data MUST be isolated per ledger; personal and group ledgers do not share items.
- **FR-018**: The system MUST validate wish list inputs (required name, non-negative numeric price, required category, optional well-formed link) and reject invalid saves with clear errors.
- **FR-019**: Deleted active items MUST NOT remain executable; executed items MUST remain visible only through the executed filter (not as active priority items).

### Key Entities

- **Wish List Item**: A planned purchase for a ledger, with name, price, category, optional product link, priority position, created time, and status (active vs executed).
- **Wish List Execution**: The confirmed conversion of an active item into an expense, linking the resulting expense back to its wish list origin for tagging and for the executed filter (which displays that expense’s final values).
- **Expense (existing)**: A recorded purchase; when originated from wish list execution, it carries a wish list origin marker for display on expense cards.
- **Ledger / Tenant context (existing)**: Personal or group spending context that owns both expenses and wish list items.
- **Budget (existing)**: Monthly limits used to explain the impact of a potential wish list purchase in the bot flow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can add a complete wish list item (name, price, category, optional link) on the web page in under 1 minute.
- **SC-002**: Users can reorder at least 5 active items by priority and see the saved order after a full page reload.
- **SC-003**: In at least 95% of successful execute flows, the resulting expense matches the values confirmed on the execute form, and the item no longer appears in the default active list.
- **SC-004**: When users enable the executed filter after purchasing via execute, 100% of those executed items are visible in the executed view.
- **SC-005**: Expense cards for wish-list-origin expenses show both category and a wish list tag; non-origin expenses never show the tag in spot checks of mixed histories.
- **SC-006**: For clear not-yet-purchased bot messages with name and price, the bot responds with budget impact and an add prompt (and does not log an expense) in the same conversational turn, and a confirmed add appears on the web Wish List within one refresh.
- **SC-007**: Ordinary expense messages without wish intent continue to log expenses successfully in regression checks (no drop in the existing happy-path expense flow).
- **SC-008**: 9 out of 10 test users can complete both (a) web create → execute → see tagged expense and (b) bot “I want to buy” → confirm add → see item on web without assistance.

## Assumptions

- Wish lists are per ledger (personal or group), matching how expenses and budgets are already scoped; any member with access to a group ledger can manage that ledger’s shared wish list.
- Categories for wish list items reuse the existing tenant category set; no separate wish list-only taxonomy.
- Amounts are in JPY only.
- Manual priority order is the default active-list presentation; “sort by created time” defaults to newest first; “sort by price” defaults to highest first (with optional reverse if the UI provides it).
- Executing creates one expense tied to one wish list item; splitting one wish item into multiple expenses is out of scope.
- On execute, the expense date defaults to the calendar day of confirmation (in the product’s existing timezone rules) and may be changed on the confirmation form before save.
- Wish list execution is web-only in v1; the LINE bot only supports detect intent → budget impact → yes/no add.


- The optional product link is stored for the user’s reference only (open externally); the product does not fetch live prices.
- Not-yet-purchased intent is recognized from clear phrases in the user’s language (at least English and Japanese examples such as “I want to buy”, “want to buy”, “買いたい”, “欲しい”, “wishlist”), consistent with the bot’s existing multilingual reply behavior.
- Ambiguous messages that do not clearly indicate “not purchased yet” follow the normal expense pipeline rather than wish list.
- Bot confirmation to add is yes/no only (using the product’s existing conversational confirm/reply patterns); no in-chat correction of name, price, category, or link — all post-add edits are on the web Wish List page.

- Budget impact in the bot uses the same cascade and fiscal-month rules as the monthly budget manager / pace alert features when budgets exist; remaining-budget figures are always shown when a budget applies, and a pace note is added only when the purchase would put spending ahead of schedule.
- v1 does not support restoring an executed item to active status; users can create a new item if needed.
- Soft-deleted or removed expenses that originated from a wish list do not automatically resurrect the wish list item.
- The executed filter is expense-centric: it shows final confirmed expense values and a link to the expense, not a preserved copy of the pre-execute planned fields for comparison.

