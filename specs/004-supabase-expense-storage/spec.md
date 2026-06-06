# Feature Specification: Supabase Expense Storage & Budget Analysis

**Feature Branch**: `004-supabase-expense-storage`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "Store expense detected into Supabase DB. Now in addition to reply the expense, this app should log expense into Supabase DB for future analysis. The schema should support features like categorize expense (can have max level 3 categories). If one expense is logged at level 3 category, it should be identifiable for level1-3. If an expense is logged at level1, it's only identifiable for level1. Standard month, yearly expense analysis. Budget setting for each level1-3 categories. Impact of one expense on the monthly budget for that category."

## Clarifications

### Session 2026-06-06

- Q: How are categories defined and how does categorization work at log time? → A: Users do not create categories upfront. The system ships a standard Japanese-family category taxonomy (up to 3 levels). The LLM best-effort guesses the category on each expense, persists the guess, and the reply always asks the user to confirm by showing the guessed category plus up to 3 alternative categories to choose from. An **Unknown** category captures items that cannot be categorized. Persisting user corrections/choice back to the database is **out of scope** for this feature (deferred to next spec).
- Q: How do users set budgets and access monthly/yearly analysis in v1? → A: **Schema only** — persist expenses with categories; data model supports future budget and analysis queries but no user-facing budget setup, budget impact in replies, or analysis commands in this feature (deferred to a follow-on budget spec).
- Q: Which timezone defines calendar month/year boundaries for aggregation? → A: **Japan Standard Time (JST / Asia/Tokyo)** for all users and all monthly/yearly rollups.
- Q: How should duplicate expense submissions be handled? → A: **Deduplicate by LINE message ID** — the same LINE message/event MUST NOT create duplicate expense records (webhook retries are idempotent).
- Q: How does the local console harness handle message identity and deduplication? → A: **Fresh synthetic message ID per run** — each console invocation (`--text` or `--image`) receives a new UUID; reruns create new records; dedup logic applies if the same synthetic ID is reused in tests.

## Out of Scope (this feature)

- User-created or user-edited category trees
- Updating stored expense category assignments based on user confirmation or correction in chat
- User-facing monthly budget setup or editing (deferred to follow-on budget spec)
- Budget impact lines in the expense log reply (deferred to follow-on budget spec)
- User-facing monthly/yearly analysis commands or dashboard UI (schema/query support only in this feature)
- Dedicated dashboard or admin UI for analysis

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Persist detected expenses when logging via the bot (Priority: P1)

A user submits an expense via text or receipt image through the LINE bot (or local console harness). After the bot successfully detects one or more expense items, it continues to reply with the expense summary as today **and** records each detected expense in persistent storage so it can be analyzed later.

**Why this priority**: Without durable storage, no monthly/yearly analysis, categorization, or budgeting is possible. This is the foundation for all other capabilities in this feature.

**Independent Test**: Submit a valid expense message, verify the user still receives the expense summary reply, and confirm one expense record exists per detected item with amount, currency, description, user identity, and timestamp.

**Acceptance Scenarios**:

1. **Given** the bot detects a single expense from a text message, **When** processing completes successfully, **Then** the user receives the expense summary reply (including guessed category, confirmation prompt, and up to 3 alternative categories) **and** exactly one expense record is stored linked to that user with the LLM-guessed category assignment.
2. **Given** the bot detects multiple expense lines from one receipt image, **When** processing completes successfully, **Then** the user receives a separate line for each expense in the reply (each with its own category guess and alternatives) **and** one stored record is created per detected item.
3. **Given** persistent storage is temporarily unavailable, **When** the bot detects an expense, **Then** the user still receives the expense summary reply **and** the failure to store is recorded for operators without exposing internal errors to the user.
4. **Given** the bot cannot detect any expense from the input, **When** processing completes, **Then** no expense record is created.
5. **Given** the LINE platform redelivers the same message event (same message ID), **When** processing runs again, **Then** no duplicate expense records are created and the user receives the same expense summary reply.

---
### User Story 2 - Auto-categorize expenses using a standard Japanese-family taxonomy (Priority: P1)

Each stored expense is associated with a category from a **predefined standard taxonomy** suitable for a typical Japanese household (up to three levels: level 1 → level 2 → level 3). Users do **not** create or configure categories before logging expenses. When an expense is detected, the system uses LLM best-effort classification against this taxonomy, persists the guessed assignment, and asks the user to confirm in the reply.

**Why this priority**: Category hierarchy is a core schema requirement and enables meaningful analysis and budget tracking without burdening users with upfront setup.

**Independent Test**: Log expenses with varied descriptions (e.g., supermarket receipt, train fare, utility bill); verify each is stored with a taxonomy category (or **Unknown**), the reply shows the guessed category path, and up to three alternative category paths for user review.

**Acceptance Scenarios**:

1. **Given** the standard taxonomy includes `食費` (L1) → `外食` (L2) → `カフェ` (L3), **When** an expense for a coffee shop is logged and the LLM assigns `カフェ` (L3), **Then** the expense is stored under that assignment and is aggregatable under `カフェ`, `外食`, and `食費`, and the reply shows the guessed category plus up to 3 alternative categories.
2. **Given** the LLM can only confidently assign at L1 (e.g., `食費`), **When** the expense is stored, **Then** it is identifiable under `食費` only and is **not** attributed to descendant L2/L3 categories, and the reply still includes confirmation with alternatives.
3. **Given** the LLM cannot map an expense to any taxonomy category with reasonable confidence, **When** the expense is stored, **Then** it is assigned to the **Unknown** category and the reply indicates Unknown as the guess with up to 3 alternatives where applicable.
4. **Given** the user replies to choose a different category from the alternatives shown, **When** they select an option, **Then** the system acknowledges the choice in chat but does **not** update the stored expense record in this feature (correction persistence deferred).
5. **Given** a category path would exceed three levels, **When** assignment is validated, **Then** the system rejects it as invalid.

---
### User Story 3 - Data model supports future monthly/yearly analysis (Priority: P2)

Stored expense data is structured so monthly and yearly spending totals can be queried by category at any hierarchy level, following the rollup rules from User Story 2. This feature delivers the **schema and queryability** only; users do not request analysis through the bot in v1.

**Why this priority**: The original request targets future analysis; laying correct aggregation foundations now avoids rework when analysis and budget features ship.

**Independent Test**: Seed expenses across two months, two years, and mixed category levels; run monthly and yearly aggregation queries and verify correct totals per period and per category rollup rules.

**Acceptance Scenarios**:

1. **Given** multiple expenses in March and April (by expense date in JST), **When** a monthly total is queried for March, **Then** the result includes only expenses whose expense date falls in March in JST.
2. **Given** expenses assigned at different category levels, **When** totals are queried for a level 1 category, **Then** the result includes expenses assigned to that level 1 category and all expenses assigned to descendant level 2 or level 3 categories under it.
3. **Given** expenses assigned only at level 1, **When** totals are queried for a level 2 category under that level 1, **Then** those level-1-only expenses are **not** included in the level 2 total.
4. **Given** expenses span two calendar years (by expense date in JST), **When** yearly totals are queried for a selected year, **Then** the result includes only expenses from that year in JST.

---

### Deferred User Stories (follow-on specs)

The following were in the original feature description but are **explicitly deferred**:

- **Set monthly budgets per category** — user-facing budget CRUD and defaults (follow-on budget spec)
- **Show budget impact when an expense is logged** — reply includes spent/limit/remaining (follow-on budget spec, depends on budget setup)

---
### Edge Cases

- Persistent storage fails after a successful expense detection: user still gets the reply; storage failure is logged for investigation.
- Receipt contains mixed currencies: each stored item keeps its own currency; analysis totals group by currency unless a conversion policy is defined (see Assumptions).
- Expense date on receipt differs from message received date: expense date defaults to receipt date when available, otherwise the log timestamp date; both are interpreted in JST for monthly/yearly grouping.
- Duplicate submission of the same LINE message (webhook retry): processing is idempotent on LINE message ID; no duplicate expense records are created.
- Local console harness: each invocation generates a fresh synthetic message ID; rerunning the same input creates new expense records unless the same synthetic ID is deliberately reused in tests.
- LLM categorization confidence is low: expense stores under **Unknown**; reply shows Unknown and alternatives.
- User selects a different category from alternatives in chat: choice is acknowledged but stored record is not updated in this feature.
- Standard taxonomy category labels are stable: historical expenses retain stable category references for accurate reports.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST persist each successfully detected expense item in durable storage in addition to returning the expense summary reply to the user.
- **FR-002**: Each stored expense MUST include at minimum: user identity, description, amount, currency, expense date, created timestamp, and source LINE message ID (when available).
- **FR-003**: The system MUST ship a predefined standard category taxonomy (up to three levels) suitable for a typical Japanese household; users MUST NOT be required to create categories before logging expenses.
- **FR-003a**: The system MUST include an **Unknown** category for expenses that cannot be mapped to the standard taxonomy with reasonable confidence.
- **FR-003b**: On each detected expense, the system MUST use LLM best-effort classification to assign a category from the standard taxonomy (or **Unknown**) and persist that assignment when the expense is stored.
- **FR-003c**: The expense summary reply MUST always include the guessed category, a confirmation prompt, and up to three alternative category paths from the standard taxonomy for the user to review.
- **FR-003d**: User category corrections or selections in chat MUST NOT update stored expense records in this feature (deferred to a follow-on spec).
- **FR-004**: When an expense is assigned to a level 3 category, the system MUST allow it to be identified and aggregated under that level 3 category and its level 2 and level 1 ancestors.
- **FR-005**: When an expense is assigned only to a level 1 category, the system MUST allow identification and aggregation at level 1 only and MUST NOT attribute it to descendant level 2 or level 3 categories.
- **FR-006**: The system MUST reject category assignments deeper than three levels.
- **FR-007**: The data model MUST support querying monthly spending totals grouped by calendar month in **JST (Asia/Tokyo)** and filterable by category at any valid hierarchy level, following the rollup rules in FR-004 and FR-005.
- **FR-008**: The data model MUST support querying yearly spending totals grouped by calendar year in **JST (Asia/Tokyo)** with the same category rollup rules as monthly analysis.
- **FR-009**: The data model MUST include structures to support per-user monthly budgets at level 1, level 2, or level 3 category nodes for a specific calendar month and currency; populating or editing budgets via the bot is **out of scope** for this feature.
- **FR-010**: The expense log reply MUST NOT include budget impact information in this feature (deferred to follow-on budget spec).
- **FR-011**: Storage failures MUST NOT prevent the user from receiving a successful expense detection reply when detection itself succeeded.
- **FR-012**: Each user's expenses and budgets MUST be isolated so one user cannot read or modify another user's data; the standard category taxonomy is shared read-only across all users.
- **FR-013**: When multiple expenses are detected in one input, the system MUST create one stored record per detected item while preserving a shared source reference (same LINE message ID) linking them to the same submission.
- **FR-014**: Expense persistence MUST be idempotent on source message ID: reprocessing the same LINE message event (or the same synthetic console message ID) MUST NOT create duplicate expense records.

### Key Entities

- **Expense Record**: A single logged spending event with description, amount, currency, expense date, user identity, source LINE message ID (shared across items from the same submission), and category assignment metadata (assigned level and category path).
- **Category Node**: A named category in the predefined standard taxonomy, up to three levels deep, with level (1–3) and optional parent. Examples: L1 `食費`, L2 `外食`, L3 `カフェ`. Includes a dedicated **Unknown** node for unclassified expenses.
- **Standard Category Taxonomy**: The system-wide Japanese-household category tree (not user-authored) used for all classification, rollups, budgets, and analysis.
- **Category Assignment**: The link between an expense and a category path, recording which level the expense was explicitly assigned at (1, 2, or 3) so rollups behave correctly.
- **Monthly Budget** *(schema placeholder)*: A future per-user spending limit for a specific category node and calendar month, expressed in a single currency; table structure exists in v1 but user-facing setup is deferred.
- **Spending Period Summary**: Aggregated totals of expense amounts for a calendar month or year, optionally filtered by category and rollup level; validated via queries in acceptance testing, not exposed to users via bot in v1.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of successfully detected expense items in acceptance testing are stored with matching amount, currency, description, and LLM-guessed category while the user receives the summary reply with confirmation and up to three alternatives within the same interaction.
- **SC-002**: Category rollup queries return correct totals in 100% of test cases covering L1-only, L2, and L3 assignments as defined in acceptance scenarios.
- **SC-003**: Monthly and yearly aggregation queries return correct totals in under 5 seconds for test datasets of up to 1,000 stored expenses per user.
- **SC-004**: Expense log replies in acceptance testing never include budget impact text (confirming v1 scope boundary).
- **SC-005**: Storage outages during acceptance testing do not reduce successful expense reply rate below existing behavior (detection reply still delivered).
- **SC-006**: Zero cross-user data leakage in authorization test cases for expenses, categories, and budgets.
- **SC-007**: Reprocessing the same LINE message ID in acceptance testing creates zero duplicate expense records across single- and multi-item submissions.

## Assumptions

- User identity is derived from the existing LINE user identifier used by the bot; the local console harness uses a documented stand-in user identity and a fresh synthetic message ID per invocation for development.
- Supabase is the designated durable storage platform per product direction; schema design supports the analysis and budget capabilities described above.
- Categories come from a **single predefined standard taxonomy** for typical Japanese household spending (e.g., food/groceries, dining out, housing/utilities, transportation, children/education, healthcare, clothing, entertainment/leisure); exact labels and hierarchy depth are finalized during planning but users never author categories in this feature.
- LLM classification uses expense description, merchant, and receipt context against the standard taxonomy; low-confidence results map to **Unknown**.
- Expenses are persisted immediately with the LLM-guessed category; confirmation in the reply is informational and does not block storage. User-driven category corrections are out of scope for this feature.
- User-facing budget setup, budget impact in replies, and analysis commands are deferred to a follow-on budget/analysis spec; this feature delivers expense persistence, categorization, and analysis-ready schema only.
- Budget and analysis amounts are computed per currency without automatic conversion; multi-currency totals are reported separately by currency.
- Expense date defaults to the date extracted from receipt or message content when available; otherwise the date of logging applies.
- Monthly and yearly analysis are validated via direct queries against stored data; no bot commands or dashboard UI in v1.
- Calendar month and year boundaries for expense dates, aggregation, and future budget periods use **Japan Standard Time (JST / Asia/Tokyo)** for all users.
- Duplicate expense records are prevented by idempotency on source message ID (LINE message ID in production; synthetic UUID per console invocation in local harness).
- Local console harness assigns a fresh synthetic message ID per run so developers can re-test the same receipt without hitting production dedup behavior; test suites may reuse a synthetic ID to verify idempotency.

## Dependencies

- Existing expense detection pipeline (text, image, OCR, and LLM assist) from prior features must remain the source of detected expense items.
- Supabase project credentials and network access must be available in deployed and local environments that exercise persistence.
- LINE webhook user identity extraction (or console harness stand-in) must be available to associate expenses with users.
