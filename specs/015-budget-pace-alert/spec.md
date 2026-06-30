# Feature Specification: Budget Pace Alert in LINE Bot Replies

**Feature Branch**: `015-budget-pace-alert`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "Add a new line bot feature. if user log an expense, and the category identified has budget, and user spend faster than expected (compared with days remain). The LLM should generate a comment to remind user they spend too fast, and their daily budget for remaining days, at the beginning of the reply. Use emoji to make it standout. User reply to update category, amount should trigger this flow as well."

## Dependencies

- Requires monthly budget configuration and budget-vs-spending calculations from the monthly budget manager feature (total, L1, and L2 budgets per ledger; expense-to-budget cascade rules).
- Requires expense logging confirmation replies and reply-based category/amount edits from existing LINE bot expense flows.

## Out of Scope (this feature)

- Budget setup or editing from the LINE bot (web console only, per existing budget manager scope)
- Standalone budget queries or spending-analysis commands outside the expense confirmation and reply-edit flows
- Push notifications, scheduled digests, or proactive messages not tied to a just-logged or just-edited expense
- Alerts for categories or ledgers with no applicable budget limit
- Custom fiscal month start day (v1 uses calendar month in Japan Standard Time, consistent with the budget manager)
- Multi-currency budget math (JPY only)
- Budget pace alerts in the web dashboard (LINE bot replies only)

## User Scenarios & Testing

### User Story 1 - Overspend reminder when logging a new expense (Priority: P1)

A user logs an expense via the LINE bot (text or receipt). The expense is assigned to a category that has an applicable monthly budget for the current fiscal month. After the expense is counted, spending in that budget bucket is ahead of the expected pace for the days remaining in the month. The bot prepends a short, eye-catching reminder at the **beginning** of its confirmation reply. The reminder states that spending is too fast and shows the recommended daily spending limit for the remaining days of the month, then continues with the normal expense confirmation content.

**Why this priority**: This is the core value — immediate feedback at the moment of spending, when users are most likely to adjust behavior.

**Independent Test**: Set a ¥30,000 L2 budget for "外食", log ¥25,000 in "外食" expenses by day 10 of a 30-day month, then log another ¥3,000 "外食" expense. Confirm the bot's reply begins with a pace warning including a daily budget figure (~¥250/day for ¥2,000 remaining over 20 days), followed by the standard confirmation.

**Acceptance Scenarios**:

1. **Given** a user with a ¥50,000 category budget and ¥40,000 already spent on day 10 of a 30-day month, **When** they log a ¥5,000 expense in that category, **Then** the bot reply begins with a pace warning (including emoji) that spending is ahead of schedule and states the daily budget for the remaining 20 days (~¥250/day), followed by the normal expense confirmation.
2. **Given** a user with a category budget who is on pace (percent spent ≤ percent of month elapsed), **When** they log an expense in that category, **Then** the bot sends the normal confirmation with **no** pace warning prepended.
3. **Given** a user logs an expense in a category with no applicable budget at any cascade level (L2, parent L1, or total), **When** the confirmation is sent, **Then** no pace warning appears regardless of overall spending.
4. **Given** a user logs a multi-item expense affecting multiple budgeted categories, **When** at least one affected budget bucket is ahead of pace after the log, **Then** the pace warning covers each ahead-of-pace bucket (or a concise combined summary if multiple), prepended before the confirmation.
5. **Given** a user logs an expense in a group chat, **When** the group's shared ledger has a budgeted category ahead of pace, **Then** the pace warning reflects the **group** ledger's budget figures, not the user's personal ledger.

---

### User Story 2 - Overspend reminder after reply-edit category or amount change (Priority: P1)

After the bot sends an expense confirmation, the user replies to that message to change the expense category or amount. The system recalculates budget impact using the same rules as a new log. If the resulting budget bucket is ahead of pace, the bot prepends the same style of pace warning at the **beginning** of its edit-summary reply.

**Why this priority**: Category and amount corrections can move spending into a budgeted bucket or worsen pace; users should get consistent guidance whenever the stored expense changes.

**Independent Test**: Log a ¥5,000 expense under an on-pace unbudgeted category, reply-edit category to a budgeted category that becomes ahead of pace, and confirm the edit reply begins with a pace warning before describing the category change.

**Acceptance Scenarios**:

1. **Given** a logged expense and the user reply-edits the **category** to one with an applicable budget that is ahead of pace after the change, **When** the edit is applied, **Then** the bot reply begins with a pace warning and daily-budget figure, then summarizes the category change.
2. **Given** a logged expense and the user reply-edits the **amount** upward in a budgeted category, **When** the new amount pushes that budget bucket ahead of pace, **Then** the bot reply begins with a pace warning reflecting the updated figures.
3. **Given** a user reply-edits category or amount and the resulting budget bucket is on pace or has no applicable budget, **When** the edit is applied, **Then** the bot sends only the normal edit summary with no pace warning.
4. **Given** a user reply-edits category from a ahead-of-pace budgeted category to one with no budget, **When** the edit is applied, **Then** no pace warning appears (pace concern no longer applies to the expense).
5. **Given** a user reply-edits only non-budget-affecting fields (e.g., description or date without changing amount or category), **When** the edit is applied, **Then** pace evaluation runs only if amount or category changed; otherwise no new pace check is required.

---

### User Story 3 - Clear, localized reminder tone with emoji (Priority: P2)

The pace warning is generated as a natural, conversational sentence (not a raw data dump) in the user's reply language. It includes at least one emoji to make the warning visually distinct from the rest of the message. The warning mentions the relevant budget category label, that spending is faster than expected, and the recommended daily spend for remaining days.

**Why this priority**: Tone and visibility determine whether users notice and act on the warning; a generic number block would be ignored.

**Independent Test**: Log an ahead-of-pace expense with the bot replying in Japanese, English, and Chinese (via user language settings or message language), and confirm each warning is conversational, includes emoji, and states the daily budget in the correct language and currency format.

**Acceptance Scenarios**:

1. **Given** an ahead-of-pace budget bucket for category "外食", **When** the bot reply language is Japanese, **Then** the warning is in Japanese, includes emoji, names the category, and states the daily budget for remaining days in ¥.
2. **Given** the same situation with English reply language, **When** the confirmation is sent, **Then** the warning is in English with equivalent meaning and formatting.
3. **Given** a pace warning is prepended, **When** the user reads the full message, **Then** the warning is visually separated from the confirmation body (e.g., blank line) so the emoji lead-in stands out.

---

### Edge Cases

- **Last day of month**: One day remains; daily budget equals the full remaining budget amount for that bucket.
- **First day of month**: Percent-of-month elapsed is minimal; if the user has already spent enough to exceed expected pace, the warning still appears.
- **Budget already exceeded (spent > limit)**: Warning still appears; daily figure reflects remaining budget (zero or negative remaining shown as ¥0/day with messaging that the budget is exhausted).
- **No days remaining** (month ended per expense date): No pace warning; fiscal month boundary rules from the budget manager apply.
- **Cascade resolution**: Expense at L3 counts against parent L2 budget if set; otherwise L1; otherwise total — pace is evaluated against the **resolved** budget bucket only.
- **Concurrent edits**: Duplicate reply protection unchanged; pace warning included in the single successful edit response.
- **Soft-deleted expense via reply**: Deletion replies do not include a pace warning (no new spending added).
- **Periodic auto-logged expenses**: Out of scope for v1 LINE confirmation flow unless they already produce a user-visible bot confirmation message.

## Requirements

### Functional Requirements

- **FR-001**: System MUST evaluate budget pace after each successful expense log that produces a user-facing confirmation reply.
- **FR-002**: System MUST evaluate budget pace after each successful reply-edit that changes an expense's **category** or **amount**.
- **FR-003**: System MUST determine the applicable budget bucket using the same cascade rules as the monthly budget manager (most specific category level with a configured limit, then parent L1, then overall total).
- **FR-004**: System MUST treat spending as "faster than expected" when the percent of budget spent exceeds the percent of the fiscal month elapsed (same pace definition as budget health coloring in the web budget view).
- **FR-005**: System MUST calculate recommended daily spend for remaining days as: `(budget limit − amount spent in bucket) ÷ days remaining in fiscal month`, rounded to a user-friendly whole currency unit for display.
- **FR-006**: When FR-004 and FR-003 conditions are met, system MUST prepend a pace warning to the **beginning** of the bot reply, before the standard confirmation or edit-summary content.
- **FR-007**: The pace warning MUST include: (a) at least one emoji, (b) an indication that spending is ahead of pace, (c) the applicable category or budget level name, and (d) the recommended daily spend for remaining days.
- **FR-008**: The pace warning MUST be generated as natural conversational text in the user's reply language (Japanese, English, or Chinese — consistent with existing bot localization).
- **FR-009**: When spending is on pace or no applicable budget exists, system MUST NOT prepend a pace warning.
- **FR-010**: For group/room expense logging, system MUST use the shared group ledger's budgets and spending totals.
- **FR-011**: For personal (1:1) expense logging, system MUST use the user's personal ledger budgets and spending totals.
- **FR-012**: When multiple budget buckets become ahead of pace from a single action, system MUST include all relevant warnings in the prepended section without omitting buckets the user would reasonably care about.
- **FR-013**: Pace warning generation MUST NOT block or replace the standard confirmation/edit reply; if warning generation fails, the user still receives the normal expense reply without the warning.

### Key Entities

- **Budget bucket**: A monthly spending limit at total, L1, or L2 level for a ledger, with tracked spent and remaining amounts for the current fiscal month.
- **Pace status**: Whether spending in a bucket is on track or ahead of schedule, derived from spent percentage versus elapsed-month percentage.
- **Daily budget (remaining)**: The even-per-day spending allowance for the rest of the fiscal month to stay within the bucket limit.
- **Pace warning**: A short prepended message block with emoji conveying ahead-of-pace status and the daily budget figure.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In test scenarios where a budgeted category is ahead of pace, 100% of expense confirmation replies include a prepended pace warning with emoji and a daily budget figure.
- **SC-002**: In test scenarios where spending is on pace or no budget applies, 0% of replies include a pace warning (no false positives).
- **SC-003**: Reply-edit category and amount changes that result in ahead-of-pace buckets trigger the warning in 100% of applicable test cases, matching new-log behavior.
- **SC-004**: Users can identify the pace warning within 3 seconds of opening the message (distinct emoji lead-in and separation from confirmation body) in usability review.
- **SC-005**: Daily budget figures shown in warnings match manual calculation from budget limit, spent total, and days remaining within rounding tolerance of ¥1.

## Assumptions

- Monthly budgets are already configured via the web dashboard; most users will have zero or few budgeted categories initially, so warnings appear only when relevant.
- "Faster than expected" uses the same pace formula as the web budget health indicator (percent spent > percent of month elapsed), ensuring consistent meaning across channels.
- Fiscal month is the calendar month in Japan Standard Time, consistent with the budget manager v1 scope.
- The warning is conversational text produced by the bot's existing language-generation capability; wording may vary slightly between messages while preserving required facts (category, ahead-of-pace, daily figure).
- Only category and amount reply-edits trigger re-evaluation; other edit types follow existing behavior without pace checks unless they indirectly change amount or category.
- Currency is JPY with standard ¥ formatting in all supported languages.
