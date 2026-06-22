# Feature Specification: Periodic Expense Scheduler

**Feature Branch**: `011-periodic-expense-scheduler`

**Created**: 2026-06-23

**Status**: Draft

**Input**: Add a new feature to the web console for logging periodic expenses automatically. Users can configure schedules for personal or group/room ledgers, choose L1 or L2 category and amount, define flexible recurrence rules (fixed-day intervals, monthly patterns, multi-month intervals, weekly weekday patterns), set start and end conditions, pause/restart/edit/delete schedules, and view all schedules in a card list with key details at a glance.

## Out of Scope (this feature)

- Creating or managing periodic schedules from the LINE bot (web console only)
- Variable or formula-based amounts (each occurrence uses the configured fixed amount unless the user edits the schedule)
- Splitting a periodic expense across multiple categories in one occurrence
- Multi-currency schedules (JPY only, consistent with the existing dashboard)
- Push notifications or LINE messages when an occurrence is logged
- Budget alerts, charts, or rollup analytics for periodic expenses
- Per-member permission roles for group schedules (any tenant member may manage, consistent with group category editing)
- Retroactive backfill of missed occurrences when a schedule was paused or the system was unavailable (see Assumptions)
- Editing individual auto-logged expense rows from the periodic schedule screen (users use the existing expense list or bot reply-edit)

## User Scenarios & Testing

### User Story 1 - Create a basic periodic expense (Priority: P1)

A signed-in user opens **Periodic Expenses** in the web console, creates a schedule for their personal ledger with a name, L2 category, fixed amount, a simple recurrence (e.g., every month on the 1st), and a start date. The schedule appears in the list showing amount, frequency, next run date, and active status.

**Why this priority**: Core value — users can automate recurring bills without manual bot logging each time.

**Independent Test**: Create a monthly rent schedule for personal tenant starting next month; confirm it appears in the card list with correct amount, category, frequency label, and next execution date.

**Acceptance Scenarios**:

1. **Given** a signed-in user on personal ledger, **When** they create a periodic expense with name, L1 or L2 category, amount, recurrence, and start date, **Then** the schedule is saved and shown as active in the list.
2. **Given** a user selects an L1 category only, **When** the schedule is saved, **Then** occurrences are logged at L1 assignment level.
3. **Given** a user selects an L2 category, **When** the schedule is saved, **Then** occurrences are logged at L2 assignment level under the correct L1.
4. **Given** required fields are missing or invalid (empty name, zero amount, no category, no recurrence), **When** the user attempts to save, **Then** validation errors are shown and nothing is saved.

---

### User Story 2 - Flexible recurrence rules (Priority: P1)

A user configures non-trivial schedules: fixed-day intervals (e.g., every 20 days), monthly patterns (specific calendar days, first day of month, last day of month, every N months on a chosen day), and weekly patterns (every N weeks on one or more weekdays).

**Why this priority**: Recurrence flexibility is the distinguishing capability of this feature.

**Independent Test**: Create three schedules — (a) every 20 days, (b) every 3 months on the 15th, (c) every 2 weeks on Monday — and verify each displays a human-readable frequency and a correct next execution date.

**Acceptance Scenarios**:

1. **Given** a user chooses "every N days" with N = 20 and start date D, **When** saved, **Then** the next execution is D and subsequent runs occur every 20 calendar days from each scheduled occurrence.
2. **Given** a user chooses monthly on day(s) 1 and 15, **When** saved, **Then** occurrences fall on those days each month (or the last day of the month when a chosen day exceeds month length).
3. **Given** a user chooses "first day of month" or "last day of month", **When** saved, **Then** the schedule runs on the correct boundary each month regardless of month length.
4. **Given** a user chooses every 3 months on the 10th with start date in January, **When** saved, **Then** occurrences align to January, April, July, October (and continue on that cadence).
5. **Given** a user chooses every 3 weeks on Wednesday, **When** saved, **Then** occurrences fall on Wednesday every third week from the anchor week containing the start date.
6. **Given** a user views a saved schedule, **When** the list or detail is shown, **Then** recurrence is summarized in plain language (e.g., "Every 20 days", "Monthly on 1st & 15th", "Every 3 months on 10th", "Every 3 weeks on Wed").

---

### User Story 3 - End conditions (Priority: P1)

A user defines when a schedule stops: never, on a specific end date, after cumulative logged amount reaches a cap, or after a set number of successful occurrences.

**Why this priority**: End rules prevent unwanted indefinite logging and support finite subscriptions or installment tracking.

**Independent Test**: Create schedules with each end type; trigger or simulate occurrences until the end condition is met; confirm the schedule moves to ended state and no further occurrences are logged.

**Acceptance Scenarios**:

1. **Given** end condition "never", **When** occurrences run over time, **Then** the schedule remains active until the user pauses, deletes, or edits it.
2. **Given** end condition "on date" with a future end date, **When** the end date passes without a matching occurrence that day, **Then** no occurrence runs after that date and the schedule shows as ended.
3. **Given** end condition "total amount" with cap 120,000 yen and amount 10,000 yen per occurrence, **When** 12 occurrences have been logged, **Then** the 13th does not run and the schedule shows as ended.
4. **Given** end condition "repeat count" with limit 6, **When** 6 occurrences have been logged, **Then** the 7th does not run and the schedule shows as ended.
5. **Given** a schedule has ended, **When** the user views the list, **Then** the card shows ended status (distinct from paused) and no next execution date.

---

### User Story 4 - Pause, restart, edit, and delete (Priority: P1)

A user pauses an active schedule to temporarily stop logging, restarts it later, edits fields (amount, category, recurrence, end rules, name), or deletes a schedule they no longer need.

**Why this priority**: Lifecycle management is essential for real-world bill changes and user control.

**Independent Test**: Pause a weekly schedule, confirm no occurrence on the next due date; restart and confirm next execution is recalculated; edit amount and verify the next occurrence uses the new amount; delete and confirm removal from list.

**Acceptance Scenarios**:

1. **Given** an active schedule, **When** the user pauses it, **Then** no occurrences run while paused and the card shows a paused indicator.
2. **Given** a paused schedule, **When** the user restarts it, **Then** it becomes active and the next execution date is the next valid occurrence on or after the restart date (not retroactive catch-up for missed dates while paused).
3. **Given** an active or paused schedule, **When** the user edits amount, category, recurrence, start/end rules, or name and saves, **Then** changes persist and the next execution date is recalculated according to the updated rules from the edit date forward.
4. **Given** any schedule the user can access, **When** the user deletes it, **Then** it is removed from the list; previously logged expenses from that schedule remain in the expense ledger unchanged.
5. **Given** an ended schedule, **When** the user attempts to restart without editing end conditions, **Then** the system prevents restart or prompts the user to adjust end rules (ended schedules cannot silently resume).

---

### User Story 5 - Group and personal tenant scope (Priority: P1)

A user creates and manages periodic expenses for their personal ledger or for a shared group/room ledger using the same tenant switcher as Expenses and Categories. Group members see and manage shared schedules for that ledger.

**Why this priority**: Matches the bot's dual personal/shared tenancy model.

**Independent Test**: User A creates a group schedule; user B (same group) sees it when switching to that group tenant; user C (not in group) does not see or modify it.

**Acceptance Scenarios**:

1. **Given** personal ledger selected, **When** the user creates a schedule, **Then** it is scoped to personal tenant only.
2. **Given** a group ledger selected, **When** a member creates a schedule, **Then** it is scoped to that group and visible to other members when they select the same tenant.
3. **Given** user switches tenant via header switcher, **When** Periodic Expenses loads, **Then** only schedules for the selected tenant are listed.
4. **Given** a user not in a group, **When** they attempt to access that group's schedules, **Then** access is denied (tenant does not appear in switcher or data is inaccessible).

---

### User Story 6 - Automatic occurrence logging (Priority: P1)

When a schedule's next execution date arrives (evaluated once per calendar day in the user's timezone), the system automatically logs an expense in the corresponding ledger with the configured amount, category, and schedule name as description, then advances the schedule to the next occurrence or ends it if an end condition is met.

**Why this priority**: Without automatic logging, the feature is only a reminder list.

**Independent Test**: Create a schedule with start date today; after the daily processing window, confirm a new expense row appears in the dashboard expense list with matching amount, category, and description, and the schedule shows an updated next execution date.

**Acceptance Scenarios**:

1. **Given** an active schedule due today, **When** daily processing runs, **Then** one expense is logged for that tenant with the configured amount and category, attributed to the user who created the schedule.
2. **Given** a successful occurrence, **When** logged, **Then** the schedule's occurrence counter and cumulative amount (if tracked) update and next execution is computed.
3. **Given** a paused or ended schedule, **When** daily processing runs, **Then** no expense is logged.
4. **Given** two schedules due the same day for the same tenant, **When** processing runs, **Then** each logs independently without duplication conflation.
5. **Given** a logged occurrence, **When** the user views the main expense list, **Then** it appears like any other expense (date = occurrence date, description = schedule name).

---

### User Story 7 - Card list overview (Priority: P2)

A user views all periodic expenses for the current tenant as scannable cards. Each card prominently shows amount, plus name, human-readable frequency, next execution date (or ended/paused state), category path, and status indicators. Cards support quick access to edit, pause/restart, and delete.

**Why this priority**: List UX drives day-to-day manageability; secondary to correct scheduling and logging.

**Independent Test**: With 5+ mixed schedules (active, paused, ended), open Periodic Expenses on mobile width and verify amount is visually dominant and key fields are readable without opening detail.

**Acceptance Scenarios**:

1. **Given** multiple schedules exist, **When** the user opens Periodic Expenses, **Then** each schedule appears as a card with name, highlighted amount, frequency summary, category (L1 or L1 › L2), next execution date or status label, and paused/ended badge when applicable.
2. **Given** an active schedule, **When** displayed on a card, **Then** amount uses stronger visual weight than other text (size, weight, or color) for at-a-glance reading.
3. **Given** no schedules for the tenant, **When** the page loads, **Then** an empty state explains how to create the first periodic expense.
4. **Given** a card, **When** the user taps edit, pause/restart, or delete, **Then** the corresponding action is available without navigating away from the list (edit may open a form sheet or page).

---

### User Story 8 - Navigation entry (Priority: P2)

Signed-in users reach Periodic Expenses from the existing side drawer alongside Expenses and Categories, with tenant switcher behavior unchanged.

**Why this priority**: Discoverability; follows established web console navigation.

**Independent Test**: Open drawer, tap Periodic Expenses, confirm route loads with current tenant selection preserved.

**Acceptance Scenarios**:

1. **Given** a signed-in user on any console page, **When** they open the side drawer, **Then** Periodic Expenses appears as a navigation item.
2. **Given** a tenant selected in the header, **When** the user navigates to Periodic Expenses, **Then** the same tenant remains selected.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow authenticated users to create periodic expense schedules scoped to a tenant (`personal`, `group`, or `room`) they can access via the existing tenant switcher.
- **FR-002**: Each schedule MUST include: display name, fixed amount in JPY, exactly one category assignment at L1 or L2 level, recurrence rule, start date, end condition, and lifecycle status (`active`, `paused`, or `ended`).
- **FR-003**: System MUST support recurrence type **fixed interval (days)**: every N calendar days (N ≥ 1) anchored from start date, with each subsequent occurrence scheduled N days after the previous scheduled occurrence.
- **FR-004**: System MUST support recurrence type **monthly on calendar day(s)**: one or more days of month (1–31), using last day of month when a day does not exist in a given month.
- **FR-005**: System MUST support recurrence type **monthly boundary**: first calendar day of each month or last calendar day of each month.
- **FR-006**: System MUST support recurrence type **every N months on a day**: every N months (N ≥ 1) on a chosen calendar day, aligned from the month of the start date.
- **FR-007**: System MUST support recurrence type **every N weeks on weekday(s)**: every N weeks (N ≥ 1) on one or more weekdays, anchored from the week containing the start date.
- **FR-008**: System MUST support end conditions: **never**; **end on date** (inclusive — occurrences on that date may run, none after); **end after cumulative logged amount** reaches a user-specified yen cap; **end after occurrence count** reaches a user-specified repeat limit.
- **FR-009**: System MUST automatically log one expense per due schedule per calendar day when status is `active`, using schedule name as expense description, configured amount and category, expense date equal to the occurrence date, and submitter attribution set to the schedule creator.
- **FR-010**: System MUST evaluate due schedules once per calendar day per schedule in the creating user's timezone (default Japan Standard Time when no preference exists).
- **FR-011**: Users MUST be able to pause an active schedule, restart a paused schedule, edit any configurable field, and delete a schedule.
- **FR-012**: Pausing MUST suppress all occurrences until restart; restarting MUST recalculate next execution from the restart date forward without backfilling missed occurrences during the pause window.
- **FR-013**: Ended schedules MUST NOT log further occurrences unless the user edits end conditions to reactivate (e.g., extend end date or raise cap) and status returns to `active`.
- **FR-014**: Deleting a schedule MUST NOT delete or alter expenses already logged from prior occurrences.
- **FR-015**: Any member of a group/room tenant MUST be able to view, create, edit, pause, restart, and delete schedules for that tenant; personal schedules MUST be accessible only to the owning user.
- **FR-016**: Periodic Expenses list MUST display each schedule as a card showing name, visually emphasized amount, human-readable frequency, category path, next execution date (if active), and clear paused or ended indicators.
- **FR-017**: Category picker MUST offer only L1 and L2 nodes from the selected tenant's taxonomy (tenant copy if initialized, else global template).
- **FR-018**: Side drawer navigation MUST include a Periodic Expenses entry consistent with Expenses and Categories pages.
- **FR-019**: System MUST prevent duplicate logging for the same schedule on the same occurrence date (idempotent daily execution per schedule).
- **FR-020**: If a schedule's assigned category is deleted from tenant taxonomy, the schedule MUST transition to `paused` and surface a clear message requiring the user to reassign category before restart.

### Edge Cases

- Start date in the past: first processing run logs if today matches a due occurrence on or after start date; otherwise next future occurrence is scheduled (no bulk backfill of all missed dates).
- Schedule edited on a day it was due: processing uses rules in effect at evaluation time; if already logged today, no second occurrence the same day unless recurrence explicitly includes multiple times per day (not supported — max one per day).
- End date equals start date: at most one occurrence on that date if rules align, then schedule ends.
- Amount cap end: partial final occurrence does not run — schedule ends when the next occurrence would exceed the cap (last logged total ≤ cap).
- Month-end monthly on 31st: February and shorter months use last day of month.
- Leap years: February 29 as a chosen monthly day runs on Feb 29 in leap years and Feb 28 (or last day) in non-leap years per month-length rule.
- User deletes account or loses tenant access: schedules remain for tenant but inaccessible to removed user; group members retain access for group schedules.
- Concurrent edit by two group members: last save wins; next execution recalculated from saved rules.
- Zero or negative amount: rejected at validation.
- Category at L2 whose parent L1 is renamed: card shows current category path from taxonomy at display time.

## Key Entities

- **Periodic expense schedule**: A user-defined recurring rule bound to one tenant, with name, amount, category assignment level, recurrence definition, start date, end condition, status, next execution date, occurrence count, cumulative logged amount, creator identity, and timestamps.
- **Recurrence rule**: Abstract schedule pattern (interval days, monthly days, monthly boundary, N-monthly day, or N-weekly weekdays) with parameters sufficient to compute the next occurrence date.
- **End condition**: One of never, end date, cumulative amount cap, or occurrence count limit; determines transition to `ended` status.
- **Schedule occurrence (logged expense)**: A standard expense ledger entry produced when a schedule fires; linked logically to the parent schedule for counting and cap tracking but editable independently via existing expense flows.
- **Tenant**: Personal or shared ledger context (same model as expenses and categories).

## Success Criteria

- **SC-001**: Users can create a periodic expense with category, amount, and recurrence in under 90 seconds on a mobile viewport.
- **SC-002**: 100% of due active schedules produce exactly one expense on the occurrence date with correct amount, category, and description (verified over a 30-day test window).
- **SC-003**: Paused schedules produce zero expenses until restarted; restarted schedules show an updated next execution within one processing cycle.
- **SC-004**: End conditions (date, amount cap, repeat count) stop logging with zero occurrences after the end state is reached.
- **SC-005**: Users can identify amount, frequency, and next run date for any active schedule from the card list without opening detail view (usability test: 90% of participants answer correctly within 5 seconds per card).
- **SC-006**: Unauthorized cross-tenant schedule access is blocked (personal and non-member group/room).

## Assumptions

- Auto-logged expenses appear in the existing expense list like bot-logged entries; no separate ledger.
- One occurrence per schedule per calendar day maximum; time-of-day is not configurable (batch daily processing).
- Missed runs during pause, ended state, or system downtime are not backfilled automatically.
- Schedule creator attribution is used for `logged_by` on auto-logged group expenses.
- UI languages follow existing ja / en / zh console i18n; recurrence summaries and validation messages are localized.
- Daily processing timezone defaults to JST; uses stored user timezone preference when the product adds or already has one for the signed-in user.
- Schedules require the tenant category taxonomy to exist (lazy-init on Categories page applies before category pick).
- Name field is user-provided (e.g., "Netflix", "家賃", "ジム会費") and doubles as the expense description on each occurrence.
