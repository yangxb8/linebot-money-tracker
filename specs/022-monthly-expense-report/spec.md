# Feature Specification: Monthly Expense Report

**Feature Branch**: `cursor/monthly-expense-report-52d2`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "I need a monthly report feature provide summary of the expense of the month. - it generates one image with graph and comments - it should consider budget and compare with expenses before give useful insight. - it should lazy run at first request of the period , tell user it will send report when they ask. Then add a new reply category user can ask to reply the report. - style needs to be consistent but also reflect things like agent setting/ overexpense / theme from highest expense"

## Clarifications

### Session 2026-11-27

- Q: When the user first asks for a month’s report and generation finishes quickly, should the bot still force a second ask, or deliver in the same turn? → A: Same-turn deliver when ready soon; otherwise acknowledge and tell the user to ask again (Option B)
- Q: When the user asks for a “monthly report” without naming a period, which period should it cover? → A: Previous completed period (Option B); if the user has defined a non-calendar reporting cycle, use that cycle’s periods instead of calendar months
- Q: Who configures the reporting cycle for this feature? → A: Consume the existing Settings → 会計月の開始日 (fiscal month start day) already in the product; this feature does not add a new cycle-configuration UI (Option A, clarified)
- Q: After a new fiscal period starts, should the bot proactively mention that last period’s report is available? → A: On the user’s first message in a new fiscal period, briefly tell them last period’s report is available when they ask (text only, no image) (Option B)
- Q: What should be the main graph on the single report image? → A: Main chart = budget vs actual (total and/or key categories); app focus is helping users meet the budget (Option A)

### Session 2026-11-27 (continued)

- Q: In a group ledger chat, who should get the new-period “report available on ask” tip? → A: Once per group conversation per period (first message from anyone; later members do not get a repeat tip) (Option B)
- Q: When total and category budgets both exist, what must the primary budget-vs-actual graph include? → A: Total plus a small set of worst-variance categories (Option C)

## Dependencies

- Reuses existing tenant/ledger access (personal and group/shared ledgers) from the LINE bot conversation context.
- Reuses expense totals and category breakdowns for the active ledger over a report period bounded by the ledger’s **会計月の開始日** (fiscal month start day) from tenant settings—day 1 means calendar months; other values shift period boundaries accordingly (same rules as budget/pace).
- Reuses monthly budget configuration and budget-vs-spending / pace rules from the monthly budget manager and budget pace alert features (total, L1, and L2 where set), aligned to the same fiscal-period boundaries the report uses.
- Reuses LINE bot behavior settings (persona/character, emoji level, custom style, reply language) so report commentary matches the user’s configured agent voice.
- Reuses the existing web **設定 → 会計月の開始日** setting; report generation only reads it (no new cycle editor in this feature).

## Out of Scope (this feature)

- Web dashboard page or downloadable PDF/CSV export of the monthly report (LINE bot image delivery only in v1)
- Unsolicited delivery of the **report image** (image is only sent in response to a monthly-report ask; the allowed new-period tip is text-only)
- Year-over-year, multi-month trend packs, or weekly/daily digest reports
- Multi-currency reporting (JPY only)
- Editing budgets or expenses from inside the report flow
- Adding or changing the 会計月の開始日 setting from the report flow (configuration remains on the existing web 設定 page)
- Sharing the report outside the ledger’s LINE conversation (e.g., public links)
- Interactive charts the user can tap to drill down (single static image only)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask for a monthly report and receive one summary image (Priority: P1)

A user asks the LINE bot for a monthly expense report (for example, “monthly report”, “今月のレポート”, “先月のまとめ”). The bot recognizes a dedicated **monthly report** request category (distinct from expense logging, wish list, and webapp-link intents). When the report for that ledger and period is ready, the bot replies with **exactly one image** that summarizes the period: a clear **budget-vs-actual** graph as the primary visual plus short written commentary/insights on the same image. The report covers the conversation’s active ledger (personal or group). When the user does not name a period, the default is the **previous completed** fiscal period per the ledger’s **会計月の開始日** (calendar month when start day is 1).

**Why this priority**: Delivering a single, readable monthly summary centered on meeting budget is the core product value.

**Independent Test**: In a ledger with budgets and categorized expenses in the target period, send a clear “monthly report” request and confirm the bot returns one image whose main graph is budget vs actual plus commentary (no expense created, no wish-list flow).

**Acceptance Scenarios**:

1. **Given** a user in a personal chat with expenses in the target period, **When** they send a message that clearly asks for the monthly report, **Then** the bot classifies it as monthly-report intent (not expense / wish list / webapp) and delivers one summary image for that personal ledger’s default or named period.
2. **Given** a user in a group ledger chat with group expenses, **When** they ask for the monthly report, **Then** the image summarizes that group ledger’s period (not a member’s personal ledger).
3. **Given** a successful report delivery when budgets apply, **When** the user inspects the image, **Then** the **primary** graph shows budget vs actual for the **total** and a **small set of worst-variance categories** (when category budgets exist), plus readable commentary/insights (not a text-only reply, and not multiple images).
4. **Given** a message that is clearly an expense or wish-list request, **When** the bot classifies intent, **Then** it does **not** treat the message as a monthly-report request.
5. **Given** a user who has not named a period and whose ledger has 会計月の開始日 = 1, **When** they ask for the monthly report, **Then** the report covers the previous completed calendar month (JST).
6. **Given** a ledger with 会計月の開始日 set to a non-1 day (e.g. 25), **When** the user asks for the monthly report without naming a period, **Then** the report covers the previous completed fiscal period for that start day (not a raw calendar month that ignores 会計月の開始日).

---

### User Story 2 - Lazy first request with same-turn delivery when ready soon (Priority: P1)

Report generation for a given ledger and month is **lazy**: it does not run until the user first requests that period’s report. On that **first request** for a period that is not yet ready, the bot starts preparing immediately. If preparation finishes soon enough for a normal conversational reply, the bot **delivers the summary image in the same turn**. If preparation needs more time, the bot does **not** leave the user in a long silent wait: it acknowledges that preparation is in progress and tells the user to **ask again** (via the monthly-report request category) to receive the report. When the user asks again after the report is ready, the bot delivers the single summary image. If the user asks again while preparation is still in progress, the bot clearly says it is still preparing and that they can ask again shortly.

**Why this priority**: Lazy generation avoids wasted work and cost for unused periods; same-turn delivery when ready soon keeps the happy path fast, while the ask-again path covers slower preparation without unsolicited image pushes.

**Independent Test**: Ask for a month’s report when preparation can finish quickly and confirm the image arrives in that same turn; ask for a slow/first-prepare case and confirm an acknowledgment to ask again, then ask again after readiness and receive the image; ask while preparation is still in progress and receive an in-progress notice (no partial/broken image).

**Acceptance Scenarios**:

1. **Given** no report has been prepared yet for ledger L and month M and preparation finishes soon enough for a normal reply, **When** the user first asks for that monthly report, **Then** the bot delivers the one summary image in the same conversational turn.
2. **Given** no report has been prepared yet for L/M and preparation needs more time than a normal reply wait, **When** the user first asks for that monthly report, **Then** the bot replies that it is preparing and that the user should ask again to receive it (and does not pretend the image was already sent).
3. **Given** preparation for L/M has finished successfully, **When** the user asks for the monthly report again, **Then** the bot sends the one summary image for L/M.
4. **Given** preparation for L/M is still running, **When** the user asks for the monthly report again, **Then** the bot says preparation is still in progress and invites them to ask again soon (without sending a partial/broken image).
5. **Given** a report for L/M was already delivered, **When** the user asks again and underlying month data has **not** changed, **Then** the bot can resend the same report without forcing the user through another “still preparing” cycle.
6. **Given** expenses or budgets for L/M changed after a report was prepared, **When** the user asks for the report again, **Then** the bot refreshes the report (lazy re-prepare as needed) so insights match current data before or as it delivers (same-turn when refresh finishes soon; otherwise ask-again acknowledgment).

---

### User Story 3 - Budget-aware insights on the report image (Priority: P1)

Because the product’s focus is helping users **meet their budget**, the report image’s **main graph is budget vs actual**. When a total budget exists, the graph **always includes total** budget vs actual. When category budgets also exist, it **also includes a small set of worst-variance categories** (most overspent or most ahead of pace)—not every budgeted L1/L2—so the image stays readable on a phone. Commentary reinforces that comparison with useful conclusions such as overall under/on/over budget, which categories drove overspend or saved room, pace vs time elapsed for the period, and practical takeaways. When only category budgets exist (no total), the primary graph uses those category budgets with the same worst-variance selection rule. When no budget is set at any applicable level, the report falls back to a spending summary graph and clearly states that no budget limit applies, without inventing fake budget pressure.

**Why this priority**: Budget comparison is the app’s core value and what turns a chart into actionable advice.

**Independent Test**: Prepare a period over total budget with several category budgets where one L2 is the worst variance; request the report and confirm the primary graph includes total plus that worst-variance category (not every category budget); repeat with a no-budget ledger and confirm fallback spending summary plus “no budget / unlimited” framing.

**Acceptance Scenarios**:

1. **Given** a total period budget and spending under that total at a healthy pace, **When** the report image is produced, **Then** the primary graph shows total budget vs actual and commentary reflects under/on-pace status (not only total spent).
2. **Given** spending over a configured total or category budget, **When** the report image is produced, **Then** the primary graph and insights clearly call out the over-budget situation and highlight worst-variance categories.
3. **Given** a total budget plus many L1/L2 budgets, **When** the report is produced, **Then** the primary graph includes the total and a **small** worst-variance category set (not every budgeted category), while commentary may still mention other drivers briefly.
4. **Given** no budgets are configured for the ledger/period, **When** the report is produced, **Then** the image uses a spending-summary fallback graph and states that no budget limit is set, without fake “over budget” warnings.
5. **Given** an in-progress current period (when the user explicitly asks for the current period), **When** the report includes pace commentary, **Then** it compares spend progress to elapsed time in that period in a way consistent with existing budget-pace concepts.

---

### User Story 4 - New-period tip that the previous report is available on ask (Priority: P2)

When a new fiscal period begins (per 会計月の開始日), on the **first message in that ledger conversation** for the new period, the bot briefly tells them that the **previous period’s report is available when they ask**—**text only**, no report image in that tip. In a **1:1** chat that is the user’s first message of the period; in a **group** chat it is once per group conversation per period (the first message from **anyone**), and later members do **not** get a repeat tip. The tip does not replace handling of the actual message intent (expense, wish list, etc.): it is an additive short notice where product rules allow combining copy, or a clear adjacent acknowledgment that does not drop the primary reply. After that tip for the conversation/period has been given, later messages in the same new period do not repeat the tip. Someone must still send a monthly-report ask to receive the image (same-turn or ask-again per User Story 2).

**Why this priority**: Surfaces the feature at a natural moment without unsolicited image spam or group tip spam; secondary to correct report delivery.

**Independent Test**: After a fiscal-period rollover, send the first message in a 1:1 and in a group and confirm a short text tip (no image); send a second message (or another member’s first message in the group) and confirm the tip is not repeated; then ask for the report and receive the image via the normal report flow.

**Acceptance Scenarios**:

1. **Given** a 1:1 ledger whose fiscal period has just rolled over and the tip has not been shown this period, **When** the user sends their first message for the new period, **Then** the bot includes a brief text notice that the previous period’s report is available when they ask, and does **not** attach the report image with that tip alone.
2. **Given** a group ledger conversation whose tip has not been shown this period, **When** any member sends the first message of the new period, **Then** the tip is shown once for that conversation; **When** another member messages later in the same period, **Then** the tip is not shown again.
3. **Given** the tip was already shown for this ledger conversation and period, **When** anyone sends another message later in the same period, **Then** the tip is not shown again.
4. **Given** someone received the tip (or the tip was shown in the group), **When** a user later sends a monthly-report ask, **Then** the normal lazy prepare / same-turn or ask-again image delivery flow runs for the previous completed period (default) or the named period.
5. **Given** the first message of the new period is itself a monthly-report ask, **When** the bot handles it, **Then** it does not require a useless separate tip-only turn—report flow takes precedence (tip may be omitted or folded into the report acknowledgment without delaying image delivery rules).

---

### User Story 5 - Consistent visual style that reflects persona, overspend, and top-spend theme (Priority: P2)

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

- What happens when the target period has **zero expenses**? The bot still completes the lazy prepare → same-turn or ask-again flow and delivers one image stating no spending, with budget context if a budget exists (e.g., fully remaining).
- What if the user asks for a period with **no ledger access** or the conversation has no resolvable ledger? The bot replies with a clear error/help message and does not generate a report image.
- What if report preparation **fails** (temporary outage)? The bot informs the user that preparation failed and that they can ask again later; it does not send a broken image.
- What if the user asks for a **future period**? The bot explains that only the current or past reporting periods are available.
- What if the user asks in a language different from the configured reply language? On-image and acknowledgment copy follow the resolved tenant reply-language rules (same as other bot replies), not a one-off language guess.
- What if two members of a **group** ask for the same period’s report? Both receive the same group-ledger report content; preparation is shared per ledger/period so the second asker does not force a confusing duplicate “first prepare” dead-end if already ready.
- What if the highest-expense category is a tiny share of spend (many equal categories)? Theme still picks a deterministic top category (tie-break stable) without implying that category alone explains the whole month if commentary would be misleading—insights should still mention overall distribution.
- What if the ledger’s **会計月の開始日** is not 1? Period boundaries, default “previous completed” selection, new-period tip timing, and budget comparison for the report follow that fiscal start day (same semantics as budget/pace); start day 1 keeps calendar months in JST.
- What if the first message of a new period is in a **group**? The tip is shown **once per group conversation per period** on the first message from anyone (text-only); later members do not get a repeat tip; the image is not sent until someone asks for the report.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize a dedicated monthly-report user request category in the LINE bot, distinct from expense, wish-list, webapp-link, and generic other intents.
- **FR-002**: Users MUST be able to request a monthly expense summary for the conversation’s active ledger (personal or group) by natural-language asks in supported reply languages (at least Japanese and English phrasing).
- **FR-003**: When the period is unspecified, the system MUST default to the **previous completed** fiscal period. Period boundaries MUST follow the ledger’s existing **会計月の開始日** (fiscal month start day) from tenant settings—day 1 means calendar months in Japan Standard Time; other values shift the fiscal month the same way budgets and pace already do. Users MUST be able to request another allowed period by naming it (e.g., “October”, “先月”, “this month” / current period).
- **FR-004**: System MUST generate **one** summary image per successful delivery that includes a primary graph and written commentary/insights. When any applicable budget exists for the period, the **primary** graph MUST be **budget vs actual**. When a total budget exists, that graph MUST include total budget vs actual; when category budgets also exist, it MUST also include a **small set of worst-variance categories** (not every budgeted L1/L2). Category spend-share alone MUST NOT be the main visual when budgets apply.
- **FR-005**: Report insights MUST compare expenses to configured budgets (total and applicable category levels) for the same period boundaries and produce useful conclusions focused on meeting the budget (under/on/over budget, drivers of variance, pace when the period is in progress), aligned with the worst-variance categories highlighted on the graph.
- **FR-006**: When no applicable budget exists, the system MUST fall back to a spending-summary graph, MUST still summarize spending, and MUST clearly indicate that no budget limit is set (no fabricated over-budget warnings).
- **FR-007**: Report preparation for a ledger/period MUST be **lazy**—work starts on the first request for that period, not on a fixed schedule and not for every unused ledger/period.
- **FR-008**: On the first request for a not-yet-ready period, the system MUST start preparation immediately. If the report becomes ready soon enough for a normal conversational reply, the system MUST deliver the summary image in that same turn; otherwise it MUST acknowledge preparation and tell the user to ask again (monthly-report request) to receive it—never silently fail or require a different channel.
- **FR-009**: On a later request after the report is ready, the system MUST deliver the summary image for that ledger/period.
- **FR-010**: While preparation is in progress, repeated asks MUST return an in-progress message and MUST NOT deliver a partial or corrupt image.
- **FR-011**: If ledger expenses or budgets for the period change after a report was prepared, the next user ask MUST result in an up-to-date report (re-prepare as needed) before treating content as final.
- **FR-012**: Report visual layout MUST stay consistent across reports (same composition family) while adapting commentary/voice to bot behavior settings (persona, emoji level, reply language).
- **FR-013**: Report styling MUST reflect over-expense severity when the month is over budget or severely ahead of pace, and MUST apply a theme/accent derived from the month’s highest-expense category without sacrificing readability.
- **FR-014**: Asking for a monthly report MUST NOT create expenses or wish-list items.
- **FR-015**: System MUST handle empty periods, preparation failures, and invalid/future periods with clear user-facing messages and no broken image delivery.
- **FR-016**: After a new fiscal period starts (per 会計月の開始日), on the first message in that ledger conversation for the new period, the system MUST briefly tell them (text only) that the previous period’s report is available when they ask; MUST NOT send the report image with that tip alone; and MUST NOT repeat the tip for later messages in the same conversation/period. In group chats this is **once per conversation per period** (first message from anyone), not once per member. If that first message is itself a monthly-report ask, report delivery rules take precedence over a separate tip-only turn.

### Key Entities

- **Monthly Report Request**: A user message classified as asking for a monthly expense report for a ledger and target report period.
- **Monthly Report Artifact**: The prepared single-image summary for one ledger and one report period, including graph data, budget comparison insights, style inputs (persona, overspend severity, top-category theme), and readiness state (not started / preparing / ready / failed).
- **Report Period**: One closed or current fiscal span for a ledger under **会計月の開始日**; calendar month in Japan Standard Time when start day is 1; defaults to the previous completed period when unspecified.
- **会計月の開始日 (Fiscal Month Start Day)**: Existing per-ledger setting (web 設定) that defines fiscal-period boundaries; the report feature reads it and does not own a new editor.
- **Budget Comparison Snapshot**: The expense totals vs configured total/L1/L2 budgets (and pace vs elapsed time when relevant) used to drive insights at preparation time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In usability checks, at least 90% of users who send a clear monthly-report request receive either the summary image (when preparation finishes soon enough) or a clear “preparing—ask again to receive” acknowledgment within one conversational turn (no silent drop).
- **SC-002**: After a period’s report is marked ready, a follow-up ask delivers the single summary image in under 10 seconds of user-perceived wait in normal conditions.
- **SC-003**: 100% of delivered report images in acceptance testing use budget vs actual as the primary graph (total plus a small worst-variance category set when both exist) and include commentary about budget performance when any budget exists for that period.
- **SC-004**: In paired reviews (over-budget vs under-budget periods; two different persona settings; two different top-spend categories), reviewers correctly identify the intended severity and persona/language differences in at least 4 of 5 samples while still recognizing the reports as the same product layout.
- **SC-005**: Zero expense or wish-list records are created as a side effect of monthly-report asks in automated acceptance scenarios.
- **SC-006**: For a ledger/period never requested, the system performs no report preparation work until the first ask (lazy behavior verified in acceptance tests).
- **SC-007**: For a ledger with 会計月の開始日 ≠ 1, an unspecified “monthly report” ask covers the previous completed fiscal period for that start day; for start day 1, it covers the previous completed calendar month (JST).
- **SC-008**: After a fiscal-period rollover, the first message in that ledger conversation yields a text-only tip about asking for the previous period’s report (no image); later messages in the same conversation/period—including other group members’ first messages—do not repeat the tip.

## Assumptions

- Default target period is the **previous completed** fiscal period; users can explicitly request the current (in-progress) period or another named past period.
- Fiscal periods follow the existing **設定 → 会計月の開始日** value already used for budget/pace; this feature only consumes that setting.
- Report **image** preparation remains lazy on the first **monthly-report ask** for that ledger/period; the new-period tip is a separate text-only notice on the first message of a new fiscal period and does not by itself start image generation.
- Image delivery is request-driven: same-turn image when preparation (or refresh) finishes soon enough; otherwise ask-again. The product does not auto-push the finished **image** as an unsolicited message in v1 (new-period tip is text-only).
- Group chats produce one shared report for the group ledger; there is no per-member split view in v1.
- “One image” means a single visual reply asset; a short accompanying text caption (e.g., “Here’s your November report”) is allowed if needed for accessibility or LINE UX, but charts and insights live on the image.
- Primary graph is budget vs actual when budgets exist: always include total when set, plus a small worst-variance category set when category budgets exist (exact chart type and “how many” categories left to planning, typically a handful for phone readability); spending-summary fallback only when no applicable budget exists.
- Highest-expense theme uses the largest spend among categories present that period; ties break deterministically.
- Reply language and persona resolution follow the same tenant/bot-behavior rules as other bot replies (including group fallback to personal settings when the shared ledger has no customization).

