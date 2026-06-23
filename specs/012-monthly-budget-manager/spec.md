# Feature Specification: Monthly Budget Manager

**Feature Branch**: `012-monthly-budget-manager`

**Created**: 2026-06-23

**Status**: Draft

**Input**: New webapp feature to manage monthly budget. Budget can be set for individual and group (shared) ledgers. Fiscal month defaults to calendar month (1st through last day); custom fiscal start day is deferred. Total budget and L1/L2 category budgets can be set. L1 defaults to the sum of its L2 children (user may add buffer). Total defaults to the sum of L1 budgets (user may add buffer). All expenses count against budget when a matching budget exists — at the detected category level first, then cascading upward (L2 → L1 → total). If no budget exists at any applicable level, the expense does not affect budget tracking. Category changes on expenses trigger budget recalculation. UI shows editable total budget, spend progress bars, and health coloring (green → red) by comparing percent budget spent to percent of fiscal month elapsed. By default there is no budget (unlimited spending).

## Out of Scope (this feature)

- Custom fiscal month start day (e.g., payday on the 25th) — reserved for a future enhancement; v1 uses calendar month only
- L3 (leaf) category budgets — only total, L1, and L2 levels are budgeted
- Budget management from the LINE bot (web console only)
- Push notifications, email alerts, or LINE messages when approaching or exceeding budget
- Multi-currency budgets (JPY only, consistent with the existing dashboard)
- Budget rollover of unused amounts to the next month
- Splitting one expense across multiple budget categories
- Per-member sub-budgets within a group ledger
- Historical budget-vs-actual charts or year-over-year analytics (simple current-month view only in v1)
- Automatic budget suggestions powered by machine learning (rule-based suggestions from past spending are in scope as a usability enhancement)

## User Scenarios & Testing

### User Story 1 - View monthly budget health at a glance (Priority: P1)

A signed-in user opens the **Budget** section in the web console for their personal or group ledger. They see the current fiscal month's overall budget (if set), amount spent, remaining amount, a progress bar showing percent spent, and a health indicator that compares spending pace to time elapsed in the month. If no budget is configured, the view clearly indicates spending is unlimited with no progress bar pressure.

**Why this priority**: The primary value is knowing whether the user is on track before they overspend.

**Independent Test**: Set a ¥100,000 total budget for the current month, log ¥70,000 in expenses by mid-month, open the budget view, and confirm the progress bar, spent/remaining amounts, and health color reflect overspending relative to days elapsed.

**Acceptance Scenarios**:

1. **Given** a user with a ¥50,000 total budget and ¥10,000 spent in the first week of a 30-day month, **When** they open the budget view, **Then** they see ~20% spent, ~33% of the month elapsed, and a healthy (green-leaning) indicator.
2. **Given** a user with a ¥50,000 total budget and ¥35,000 spent in the first week of a 30-day month, **When** they open the budget view, **Then** they see ~70% spent, ~23% of the month elapsed, and an unhealthy (red-leaning) indicator.
3. **Given** a user with no budget configured for any level, **When** they open the budget view, **Then** they see current-month spending totals with an "unlimited" or "no budget set" state and no misleading progress bar.
4. **Given** a user switches from personal to group ledger, **When** the budget view loads, **Then** it shows that group's independent budget and spending (not the personal ledger's).

---

### User Story 2 - Set and edit total, L1, and L2 budgets (Priority: P1)

A user configures monthly budgets at total, L1, and/or L2 levels for the active ledger. When they add or change L2 amounts under an L1, the L1 suggested amount updates to the sum of its L2 children; the user may accept the suggestion or enter a higher amount (buffer). When L1 amounts change, the total suggested amount updates to the sum of L1 budgets; the user may accept or add buffer at the total level. Saving persists budgets for the selected month and ledger.

**Why this priority**: Without configurable limits, budget tracking cannot begin.

**Independent Test**: Set L2 budgets for two categories under "食費", confirm L1 auto-suggests their sum, add a ¥5,000 buffer at L1, confirm total auto-suggests sum of all L1 budgets, add buffer at total, save, and reload to verify persistence.

**Acceptance Scenarios**:

1. **Given** a user editing L2 budgets under an L1 category, **When** they enter amounts for each L2 child, **Then** the L1 field suggests the arithmetic sum and the user can override it with a higher value (buffer).
2. **Given** L1 budgets are set or updated, **When** the user views the total budget field, **Then** it suggests the sum of all L1 budgets and the user can override with a higher value (buffer).
3. **Given** a user sets only a total budget with no L1/L2 budgets, **When** they save, **Then** only total-level tracking is active for the month.
4. **Given** a user sets only an L2 budget for one category, **When** they save, **Then** expenses matching that L2 (or its L3 children) count against that L2 budget; other categories are unaffected unless their own budgets exist.
5. **Given** invalid input (negative amount, non-numeric), **When** the user attempts to save, **Then** validation errors are shown and nothing is saved.
6. **Given** a user clears a previously set budget amount for a level, **When** they save, **Then** that level returns to unlimited (no limit) for the month.

---

### User Story 3 - Expenses automatically count against applicable budgets (Priority: P1)

When an expense is logged (via bot, periodic scheduler, or any existing ingestion path), the system counts its amount against the current fiscal month's budget at the most specific matching level. Expenses assigned at L3 cascade to their parent L2, then L1, then total. If no budget exists at any level in the cascade, the expense is recorded but does not affect budget figures.

**Why this priority**: Automatic tracking is the core mechanism; manual reconciliation would defeat the purpose.

**Independent Test**: Set an L2 budget for "外食" only, log expenses at L3 "カフェ" and at L2 "外食", confirm both count against the "外食" L2 budget; log an expense in an unrelated L1 with no budgets and confirm it does not affect any budget meter.

**Acceptance Scenarios**:

1. **Given** an L2 budget exists for category X and an expense is assigned at L3 under X, **When** the expense is saved, **Then** the L2 budget for X reflects the expense amount.
2. **Given** no L2 budget for category X but an L1 budget exists for X's parent L1, **When** an expense is assigned at L2 or L3 under that L1, **Then** the L1 budget reflects the expense amount.
3. **Given** only a total budget is set (no category budgets), **When** any expense is logged, **Then** the total budget reflects the expense amount.
4. **Given** no budget at any level, **When** an expense is logged, **Then** spending totals update but no budget progress or health indicators change.
5. **Given** an expense is soft-deleted, **When** budget figures are viewed, **Then** the deleted expense no longer counts toward spent amounts.
6. **Given** a periodic expense occurrence is auto-logged, **When** budget is viewed, **Then** that occurrence counts the same as a manually logged expense.

---

### User Story 4 - Category changes recalculate budget impact (Priority: P1)

When a user changes an expense's category (via bot reply-edit or any supported category-update flow), the system removes the expense from the old budget bucket(s) and applies it to the new bucket(s) using the same cascade rules. Amount changes on an expense likewise update budget spent figures.

**Why this priority**: Incorrect budget figures after edits would quickly erode user trust.

**Independent Test**: Log a ¥3,000 expense under "外食", confirm L2 budget shows ¥3,000 spent, reply-edit category to "食料品", confirm "外食" decreases by ¥3,000 and "食料品" increases by ¥3,000 (when respective budgets exist).

**Acceptance Scenarios**:

1. **Given** an expense counted against L2 budget A, **When** the category is changed so it should count against L2 budget B, **Then** spent amounts for A decrease and B increase by the expense amount.
2. **Given** an expense counted against total budget only, **When** its amount is edited from ¥1,000 to ¥1,500, **Then** total spent increases by ¥500.
3. **Given** an expense moves from a budgeted category to one with no applicable budget, **When** the category change is saved, **Then** the old budget bucket is reduced and no new bucket is incremented.
4. **Given** a category change moves an expense across fiscal months (expense date changes), **When** saved, **Then** both the old and new months' budget figures are recalculated correctly.

---

### User Story 5 - Drill down into L1 and L2 budget breakdown (Priority: P2)

A user expands the budget view to see each L1 category with its own progress bar, health color, spent/remaining amounts, and nested L2 rows where L2 budgets exist. They can edit any level inline or via an edit flow without leaving the page.

**Why this priority**: Total-only visibility is insufficient for users managing category-level limits.

**Independent Test**: Set budgets at total, two L1 categories, and one L2 under the first L1; confirm the breakdown shows three progress bars with correct independent health colors.

**Acceptance Scenarios**:

1. **Given** L1 and L2 budgets are configured, **When** the user expands the budget breakdown, **Then** each budgeted L1 and L2 shows spent, limit, remaining, progress bar, and health color.
2. **Given** an L1 has L2 children with budgets but the L1 itself has no explicit budget, **When** viewing the breakdown, **Then** the L1 row shows aggregated spent from its L2 budgets (or from expenses cascading to L1) without implying an L1 limit exists.
3. **Given** a user taps edit on an L2 budget row, **When** they change the amount and save, **Then** the L1 suggested total and health indicators update without a full page reload.

---

### User Story 6 - Quick budget setup helpers (Priority: P3)

A user setting up budgets for the first time can copy the previous month's budget amounts, or apply suggested amounts based on average spending over the prior three months per category. These are optional shortcuts; manual entry remains fully supported.

**Why this priority**: Reduces friction for recurring monthly budget setup without blocking core functionality.

**Independent Test**: With three months of expense history, tap "Suggest from past spending" on an L2 row and confirm the suggested amount equals the three-month average for that category.

**Acceptance Scenarios**:

1. **Given** a user had budgets last month, **When** they choose "Copy from last month", **Then** all budget amounts from the prior fiscal month are pre-filled for the current month (user still confirms save).
2. **Given** three months of expense history for an L2 category, **When** the user requests a spending-based suggestion, **Then** the system proposes the rounded average monthly spend for that category.
3. **Given** no prior month budget or insufficient history, **When** the user requests a shortcut, **Then** the action is disabled or explains why it is unavailable.

---

### Edge Cases

- Expense amount is zero or negative: excluded from budget spent calculations (consistent with expense validation rules).
- User sets L1 budget lower than the sum of its L2 budgets: allowed; L2 meters may show over-budget while L1 shows a different figure — each level tracks independently.
- User sets total budget lower than the sum of L1 budgets: allowed; levels track independently.
- Expense logged on the last day of the month at 23:59 JST: counts toward that fiscal month based on expense date, not log timestamp.
- First day of a new month with no budgets copied forward: all levels return to unlimited until the user configures new amounts.
- Group member logs expense after another member set the group budget: expense counts against the shared group budget immediately.
- User views budget on day 1 of the month with 0% time elapsed: health indicator uses a neutral or "too early to judge" state rather than dividing by zero.
- Large volume of expenses in one category: progress bar caps at 100% visually but shows actual percent (e.g., "135%") in text when over budget.
- Category deleted or merged (tenant category editor): expenses reassigned per existing category-editor rules trigger the same budget recalculation as a category change.

## Requirements

### Functional Requirements

- **FR-001**: System MUST support independent monthly budgets per ledger (personal user ledger and each group/room shared ledger the user can access).
- **FR-002**: System MUST default the fiscal month to the calendar month (1st 00:00 through last day 23:59:59 in Japan Standard Time) for v1.
- **FR-003**: System MUST allow setting optional budget amounts at three levels: overall total, L1 category, and L2 category.
- **FR-004**: System MUST default to unlimited (no budget limit) at every level until the user explicitly sets an amount.
- **FR-005**: When the user edits L2 budgets under an L1, the system MUST suggest the L1 amount as the sum of those L2 amounts; the user MUST be able to save a higher L1 value (buffer).
- **FR-006**: When L1 budgets are present, the system MUST suggest the total budget as the sum of L1 amounts; the user MUST be able to save a higher total value (buffer).
- **FR-007**: System MUST count each non-deleted expense toward the current fiscal month's budget using this cascade: attempt the budget at the expense's assigned category level (L2 for L2/L3 expenses, L1 for L1 expenses); if none exists, attempt the parent L1; if none exists, attempt the overall total; if none exists at any level, skip budget counting for that expense.
- **FR-008**: System MUST recalculate budget spent figures when an expense's amount, category, expense date, or deletion status changes.
- **FR-009**: System MUST include auto-logged periodic expenses in budget spent calculations using the same rules as manually logged expenses.
- **FR-010**: Budget UI MUST display for the active ledger: budget limit (if set), amount spent, amount remaining, and percent spent for the overall total and for each configured L1/L2 budget.
- **FR-011**: Budget UI MUST show a progress bar for each level that has a configured limit.
- **FR-012**: Budget UI MUST show a health color from green (on pace) to red (overspending relative to time) by comparing percent of budget spent to percent of the fiscal month elapsed.
- **FR-013**: Users MUST be able to view and edit budget amounts for the current fiscal month from the web console.
- **FR-014**: System MUST persist budget configurations and reflect updates without requiring users to re-log expenses.
- **FR-015**: When a user first sets a budget mid-month, spent amounts MUST include all qualifying expenses already logged in that fiscal month up to that point.
- **FR-016**: System MUST provide an optional "copy from last month" action to pre-fill budget amounts.
- **FR-017**: System MUST provide an optional per-category suggestion based on the average monthly spend over the prior three fiscal months where data exists.
- **FR-018**: Budget views MUST respect the same tenant switcher (personal vs group/room) as the existing expense dashboard.
- **FR-019**: Any group member who can access the group ledger in the web console MUST be able to view and edit that group's budgets (consistent with group category management permissions).

### Key Entities

- **Monthly Budget**: A spending limit for a specific ledger, fiscal month, and budget level (total, L1, or L2). Attributes: ledger identity, fiscal month, target level, category reference (null for total), amount, currency. Absence of a record means unlimited at that level.
- **Budget Spent Snapshot**: Derived figures for a ledger and fiscal month showing how much has been counted against each configured budget level. Not a separate user-editable entity; computed from expenses and budget rules.
- **Fiscal Month**: The time window for budget tracking. V1 uses calendar months in JST. Identified by year-month.
- **Budget Health**: A derived status comparing spending pace (percent of budget used) to time pace (percent of fiscal month elapsed) for visual feedback.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can set or update a total monthly budget and see updated progress within 5 seconds of saving, without re-entering expenses.
- **SC-002**: 100% of qualifying expenses logged through any existing ingestion path appear in budget spent totals within the same session the expense is recorded.
- **SC-003**: Category or amount edits on an expense update all affected budget meters accurately in 100% of tested scenarios (no stale spent amounts after edit).
- **SC-004**: Users can identify whether they are over-spending relative to the month timeline within 3 seconds of opening the budget view (single glance at health color and progress bar).
- **SC-005**: 90% of test users can configure a total plus two category budgets on first attempt without documentation.
- **SC-006**: Budget view correctly isolates personal vs group ledger data with zero cross-ledger leakage in all tested tenant-switch scenarios.

## Assumptions

- Budgets apply only to JPY amounts; expenses in other currencies are out of scope (consistent with the existing dashboard).
- The web console remains the sole interface for budget management; the LINE bot does not display budget status in v1.
- Expense category taxonomy remains L1/L2 in the web category editor; L3 assignments from bot categorization map to parent L2 for budget cascade purposes.
- "Buffer" means the user may set a parent budget higher than the sum of children; the system does not enforce that parent ≥ sum(children).
- Health color on day 1 of the month (0% time elapsed) shows a neutral state until at least one full day has elapsed, or uses a minimum 1-day denominator to avoid extreme colors.
- Budget amounts do not auto-carry to the next month; users copy manually or via the copy shortcut.
- Retroactive recalculation when budgets are first set mid-month uses expense date to determine fiscal month membership.
- Group budget editing follows the same open permission model as group category editing (any member with dashboard access).

## Usability Enhancements (proposed)

- **Pace comparison label**: Show plain-language text alongside color, e.g., "Spending faster than this month" or "On track", so color-blind users are not reliant on hue alone.
- **Remaining days and daily allowance**: Display "¥X remaining · ¥Y/day for Z days left" based on current pace to help users self-correct.
- **Over-budget emphasis**: When spent exceeds 100%, show the overrun amount prominently (e.g., "¥5,000 over budget") not only a maxed progress bar.
- **Unbudgeted spending callout**: Surface spending in categories with no L2/L1 limit so users know where "invisible" spend is occurring.
- **Inline expand/collapse**: Default to collapsed L1 rows with only over-budget or near-limit categories highlighted expanded.
- **Copy and suggest shortcuts**: "Copy last month" at the top level; per-row "Suggest from 3-month average" as described in User Story 6.
- **Empty-state onboarding**: First visit shows a short explanation and a one-tap "Start with suggested budgets" using three-month averages.
- **Month navigator**: Allow viewing prior months' budget vs actual (read-only) to inform the current month's setup; editing remains limited to current and future months in v1.
- **Consistent health across levels**: When an L2 is red but total is green, show both honestly so users can see localized vs overall health.
