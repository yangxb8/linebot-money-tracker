# Feature Specification: Monthly Expense Report

**Feature Branch**: `cursor/monthly-expense-report-52d2`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "I need a monthly report feature provide summary of the expense of the month. - it generates one image with graph and comments - it should consider budget and compare with expenses before give useful insight. - it should lazy run at first request of the period , tell user it will send report when they ask. Then add a new reply category user can ask to reply the report. - style needs to be consistent but also reflect things like agent setting/ overexpense / theme from highest expense"

## Dependencies

- Reuses existing tenant/ledger access (personal and group/shared ledgers) from the LINE bot conversation context.
- Reuses calendar-month expense totals and category breakdowns already available for each ledger.
- Reuses monthly budget configuration and budget-vs-spending / pace rules from the monthly budget manager and budget pace alert features (total, L1, and L2 where set).
- Reuses LINE bot behavior settings (persona/character, emoji level, custom style, reply language) so report commentary matches the user’s configured agent voice.

## Out of Scope (this feature)

- Web dashboard page or downloadable PDF/CSV export of the monthly report (LINE bot image delivery only in v1)
- Scheduled push that delivers the report image without the user asking (no unsolicited report image spam)
- Year-over-year, multi-month trend packs, or weekly/daily digest reports
- Custom fiscal month start day (v1 uses calendar month in Japan Standard Time, consistent with budgets)
- Multi-currency reporting (JPY only)
- Editing budgets or expenses from inside the report flow
- Sharing the report outside the ledger’s LINE conversation (e.g., public links)
- Interactive charts the user can tap to drill down (single static image only)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask for a monthly report and receive one summary image (Priority: P1)

A user asks the LINE bot for a monthly expense report (for example, “monthly report”, “今月のレポート”, “先月のまとめ”). The bot recognizes a dedicated **monthly report** request category (distinct from expense logging, wish list, and webapp-link intents). When the report for that ledger and month is ready, the bot replies with **exactly one image** that summarizes the month: a clear spending graph plus short written commentary/insights on the same image. The report covers the conversation’s active ledger (personal or group).

**Why this priority**: Delivering a single, readable monthly summary on request is the core product value.

**Independent Test**: In a ledger with several categorized expenses in the target month, send a clear “monthly report” request and confirm the bot returns one image containing both a graph and commentary (no expense created, no wish-list flow).

**Acceptance Scenarios**:

1. **Given** a user in a personal chat with expenses in the target month, **When** they send a message that clearly asks for the monthly report, **Then** the bot classifies it as monthly-report intent (not expense / wish list / webapp) and delivers one summary image for that personal ledger.
2. **Given** a user in a group ledger chat with group expenses, **When** they ask for the monthly report, **Then** the image summarizes that group ledger’s month (not a member’s personal ledger).
3. **Given** a successful report delivery, **When** the user inspects the image, **Then** it includes both a spending graph and readable commentary/insights in one composition (not a text-only reply with a separate bare chart, and not multiple images).
4. **Given** a message that is clearly an expense or wish-list request, **When** the bot classifies intent, **Then** it does **not** treat the message as a monthly-report request.

---

### User Story 2 - Lazy first request, then ask again to receive the report (Priority: P1)

Report generation for a given ledger and month is **lazy**: it does not run until the user first requests that period’s report. On that **first request** for a period that is not yet ready, the bot does **not** block the user with a long silent wait. Instead it acknowledges the request, starts preparing the report in the background, and tells the user that it will **send the report when they ask** (via the monthly-report request category). When the user asks again after the report is ready, the bot delivers the single summary image. If the user asks again while preparation is still in progress, the bot clearly says it is still preparing and that they can ask again shortly.

**Why this priority**: Lazy generation avoids wasted work and cost for unused periods; the ask-to-receive pattern keeps delivery under user control and matches the requested UX.

**Independent Test**: Ask for a month’s report for the first time, confirm an acknowledgment that preparation has started and that asking again will deliver it; ask again after readiness and receive the image; ask once more while a slow preparation is in progress and receive an in-progress notice (no duplicate conflicting images).

**Acceptance Scenarios**:

1. **Given** no report has been prepared yet for ledger L and month M, **When** the user first asks for that monthly report, **Then** the bot replies that it is preparing the report and that the user should ask for the report when they want it delivered (and does not pretend the image was already sent).
2. **Given** preparation for L/M has finished successfully, **When** the user asks for the monthly report again, **Then** the bot sends the one summary image for L/M.
3. **Given** preparation for L/M is still running, **When** the user asks for the monthly report again, **Then** the bot says preparation is still in progress and invites them to ask again soon (without sending a partial/broken image).
4. **Given** a report for L/M was already delivered, **When** the user asks again and underlying month data has **not** changed, **Then** the bot can resend the same report without forcing the user through another “still preparing” cycle.
5. **Given** expenses or budgets for L/M changed after a report was prepared, **When** the user asks for the report again, **Then** the bot refreshes the report (lazy re-prepare as needed) so insights match current data before or as it delivers.

---

### User Story 3 - Budget-aware insights on the report image (Priority: P1)

The commentary and highlights on the report image are grounded in a comparison of **actual expenses vs configured budgets** for that month (total and category levels where budgets exist), not only a raw spend total. Insights call out useful conclusions such as overall under/on/over budget, which categories drove spend, pace vs time elapsed for the month, and practical takeaways (for example, where the user is ahead of pace or already over a limit). When no budget is set at any applicable level, the report still summarizes spending by category and clearly states that no budget limit applies, without inventing fake budget pressure.

**Why this priority**: Budget comparison is what turns a chart into actionable advice.

**Independent Test**: Prepare a month that is over total budget with one dominant category over its L2 budget; request the report and confirm the image commentary mentions budget comparison and the overspending categories; repeat with a no-budget ledger and confirm “no budget / unlimited” framing with category summary only.

**Acceptance Scenarios**:

1. **Given** a total monthly budget and spending under that total at a healthy pace, **When** the report image is produced, **Then** commentary reflects under/on-pace status using budget vs actual (not only total spent).
2. **Given** spending over a configured total or category budget, **When** the report image is produced, **Then** insights clearly call out the over-budget situation and the main contributing categories.
3. **Given** category (L1/L2) budgets exist, **When** the report is produced, **Then** insights consider those levels (not only the total) when explaining where money went relative to limits.
4. **Given** no budgets are configured for the ledger/month, **When** the report is produced, **Then** the image still shows spending summary/graph and states that no budget limit is set, without fake “over budget” warnings.
5. **Given** an in-progress current month, **When** the report includes pace commentary, **Then** it compares spend progress to elapsed time in the month in a way consistent with existing budget-pace concepts.

---

### User Story 4 - Consistent visual style that reflects persona, overspend, and top-spend theme (Priority: P2)

Every report image follows a **consistent layout and brand frame** (same overall composition rules so reports feel like one product). Within that frame, visual mood and commentary voice adapt to: (1) the ledger’s **bot behavior / agent settings** (persona tone, emoji level, reply language for on-image text), (2) **over-expense severity** (noticeably more cautionary styling/copy when over budget or badly ahead of pace), and (3) a **theme drawn from the highest-expense category** for the month (for example, color accent or motif aligned with the top spending category), without breaking readability or the shared layout.

**Why this priority**: Personality and situational theming increase engagement, but only after the summary and insights are correct.

**Independent Test**: Generate reports for the same month under two different persona/language settings and confirm voice/language follow settings while layout stays consistent; generate an over-budget month vs under-budget month and confirm stronger caution cues when over; confirm the accent/theme tracks the highest-spend category.

**Acceptance Scenarios**:

1. **Given** two ledgers (or settings changes) with different persona and reply-language settings, **When** each receives a report for comparable data, **Then** on-image commentary matches each setting’s language and persona tone while the overall layout structure remains the same family.
2. **Given** a month that is over budget (or severely ahead of pace) versus a healthy under-budget month, **When** both reports are produced, **Then** the over-budget report uses clearly more cautionary visual/copy cues while remaining readable and on-brand.
3. **Given** a month whose highest spending category is Food versus one whose highest is Transport, **When** reports are produced, **Then** each image’s theme/accent reflects its top-spend category while graph labels and insights stay legible.
4. **Given** emoji level is set low/off versus high, **When** reports are produced, **Then** on-image commentary respects that emoji level.

---

### Edge Cases

- What happens when the target month has **zero expenses**? The bot still completes the lazy prepare → ask-to-receive flow and delivers one image stating no spending, with budget context if a budget exists (e.g., fully remaining).
- What if the user asks for a month with **no ledger access** or the conversation has no resolvable ledger? The bot replies with a clear error/help message and does not generate a report image.
- What if report preparation **fails** (temporary outage)? The bot informs the user that preparation failed and that they can ask again later; it does not send a broken image.
- What if the user asks for a **future month**? The bot explains that only the current or past calendar months are available.
- What if the user asks in a language different from the configured reply language? On-image and acknowledgment copy follow the resolved tenant reply-language rules (same as other bot replies), not a one-off language guess.
- What if two members of a **group** ask for the same month’s report? Both receive the same group-ledger report content; preparation is shared per ledger/month so the second asker does not force a confusing duplicate “first prepare” dead-end if already ready.
- What if the highest-expense category is a tiny share of spend (many equal categories)? Theme still picks a deterministic top category (tie-break stable) without implying that category alone explains the whole month if commentary would be misleading—insights should still mention overall distribution.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize a dedicated monthly-report user request category in the LINE bot, distinct from expense, wish-list, webapp-link, and generic other intents.
- **FR-002**: Users MUST be able to request a monthly expense summary for the conversation’s active ledger (personal or group) by natural-language asks in supported reply languages (at least Japanese and English phrasing).
- **FR-003**: When the month is unspecified, the system MUST default the report period to the **current calendar month** in Japan Standard Time; users MUST be able to request a **past** calendar month by naming it (e.g., “October”, “先月”).
- **FR-004**: System MUST generate **one** summary image per successful delivery that includes both a spending graph and written commentary/insights.
- **FR-005**: Report insights MUST compare expenses to configured budgets (total and applicable category levels) and produce useful conclusions (under/on/over budget, drivers of spend, pace when the month is in progress).
- **FR-006**: When no applicable budget exists, the system MUST still summarize spending and MUST clearly indicate that no budget limit is set (no fabricated over-budget warnings).
- **FR-007**: Report preparation for a ledger/month MUST be **lazy**—work starts on the first request for that period, not on a fixed schedule and not for every unused ledger/month.
- **FR-008**: On the first request for a not-yet-ready period, the system MUST acknowledge preparation and tell the user the report will be sent when they ask for it (monthly-report request), rather than silently failing or requiring a different channel.
- **FR-009**: On a later request after the report is ready, the system MUST deliver the summary image for that ledger/month.
- **FR-010**: While preparation is in progress, repeated asks MUST return an in-progress message and MUST NOT deliver a partial or corrupt image.
- **FR-011**: If ledger expenses or budgets for the period change after a report was prepared, the next user ask MUST result in an up-to-date report (re-prepare as needed) before treating content as final.
- **FR-012**: Report visual layout MUST stay consistent across reports (same composition family) while adapting commentary/voice to bot behavior settings (persona, emoji level, reply language).
- **FR-013**: Report styling MUST reflect over-expense severity when the month is over budget or severely ahead of pace, and MUST apply a theme/accent derived from the month’s highest-expense category without sacrificing readability.
- **FR-014**: Asking for a monthly report MUST NOT create expenses or wish-list items.
- **FR-015**: System MUST handle empty months, preparation failures, and invalid/future months with clear user-facing messages and no broken image delivery.

### Key Entities

- **Monthly Report Request**: A user message classified as asking for a monthly expense report for a ledger and target calendar month.
- **Monthly Report Artifact**: The prepared single-image summary for one ledger and one calendar month, including graph data, budget comparison insights, style inputs (persona, overspend severity, top-category theme), and readiness state (not started / preparing / ready / failed).
- **Report Period**: A calendar month in Japan Standard Time for a specific ledger; defaults to the current month when unspecified.
- **Budget Comparison Snapshot**: The expense totals vs configured total/L1/L2 budgets (and pace vs elapsed time when relevant) used to drive insights at preparation time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In usability checks, at least 90% of users who send a clear monthly-report request receive either a clear “preparing—ask again to receive” acknowledgment or the summary image within one conversational turn (no silent drop).
- **SC-002**: After a period’s report is marked ready, a follow-up ask delivers the single summary image in under 10 seconds of user-perceived wait in normal conditions.
- **SC-003**: 100% of delivered report images in acceptance testing include both a spending graph and commentary that mentions budget vs actual when any budget exists for that month.
- **SC-004**: In paired reviews (over-budget vs under-budget months; two different persona settings; two different top-spend categories), reviewers correctly identify the intended severity and persona/language differences in at least 4 of 5 samples while still recognizing the reports as the same product layout.
- **SC-005**: Zero expense or wish-list records are created as a side effect of monthly-report asks in automated acceptance scenarios.
- **SC-006**: For a ledger/month never requested, the system performs no report preparation work until the first ask (lazy behavior verified in acceptance tests).

## Assumptions

- Calendar months use Japan Standard Time boundaries, matching existing budget/expense month semantics.
- Default target month is the **current** calendar month; “先月” / explicit month names select a past month.
- “Lazy run at first request of the period” means the first **monthly-report ask** for that ledger/month starts preparation—not the first arbitrary chat message of the month.
- Delivery remains ask-based: the product may tell the user to ask for the report, but does not auto-push the finished image as an unsolicited message in v1.
- Group chats produce one shared report for the group ledger; there is no per-member split view in v1.
- “One image” means a single visual reply asset; a short accompanying text caption (e.g., “Here’s your November report”) is allowed if needed for accessibility or LINE UX, but charts and insights live on the image.
- Graph content at minimum shows spending breakdown suitable for a month summary (e.g., by category and/or budget comparison); exact chart type is an implementation choice left to planning.
- Highest-expense theme uses the largest spend among categories present that month; ties break deterministically.
- Reply language and persona resolution follow the same tenant/bot-behavior rules as other bot replies (including group fallback to personal settings when the shared ledger has no customization).
