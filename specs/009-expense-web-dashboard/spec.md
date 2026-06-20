# Feature Specification: Expense Web Dashboard

**Feature Branch**: `009-expense-web-dashboard`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Mobile-first website for LINE bot users. MVP uses LINE Login to authenticate and shows logged expenses in a read-only dashboard. Users can switch between personal and group/room ledgers. Deployed on Vercel; data access via Supabase with row-level security. Bot exposes a rich menu link to the dashboard.

## Clarifications

### Session 2026-06-19

- Q: LINE auth entry point? → A: **Both** — LINE Login in external browser and LIFF inside the LINE app.
- Q: Auth platform? → A: **Supabase Auth** — sessions issued through Supabase; identity linked to existing `line_user_id`.
- Q: Identity join key? → A: **LINE `userId`** matches `expenses.line_user_id` / personal `tenant_id`; `local_run` test users are out of scope.
- Q: Dashboard tenant scope? → A: **Personal plus group/room** — user can switch between personal ledger and any shared ledger they belong to.
- Q: Minimum dashboard content? → A: **Paginated expense list** (date, description, amount, category); no charts or rollup summaries in MVP.
- Q: Write access? → A: **Read-only** — edits remain in the LINE bot (reply-edit flow).
- Q: Frontend approach? → A: **Next.js (React)** on Vercel for developer convenience.
- Q: Data access pattern? → A: **Supabase client + RLS** for MVP; Edge Functions deferred for future complex features.
- Q: Locale and currency? → A: **JPY only** for display; UI languages **ja / en / zh** aligned with bot language preferences.
- Q: LINE channel and deployment? → A: **Same Messaging API channel** for Login; host on `*.vercel.app` for now; bot exposes **rich menu** link to dashboard.

## Out of Scope (this feature)

- Creating, editing, or deleting expenses from the web
- Monthly category rollups, charts, or budget views
- Multi-currency display or conversion (non-JPY rows may be hidden or shown as unsupported)
- `local_run` / console test user access
- Custom domain or production hardening beyond HTTPS
- Paid tiers, usage quota display, or admin console
- LINE profile display names in expense list (submitter attribution deferred)
- Push notifications or real-time sync
- Supabase Edge Functions for dashboard APIs (reserved for future)

## User Scenarios & Testing

### User Story 1 - Sign in with LINE (Priority: P1)

A LINE bot user opens the expense dashboard and signs in with their LINE account. Sign-in works both in a mobile browser (LINE Login) and inside the LINE app (LIFF). After authentication, the user lands on their expense list without creating a separate username or password.

**Why this priority**: Without trusted identity, no expense data can be shown safely.

**Independent Test**: Open the dashboard URL, complete LINE sign-in, and confirm the session persists across page refresh until logout or expiry.

**Acceptance Scenarios**:

1. **Given** an unauthenticated visitor on a mobile browser, **When** they tap "Sign in with LINE" and approve the LINE Login consent screen, **Then** they are redirected to the dashboard with an active session tied to their LINE user ID.
2. **Given** a user opens the dashboard from the LINE in-app browser via LIFF, **When** they are already logged into LINE, **Then** they are signed in automatically or with minimal interaction and see the dashboard.
3. **Given** a user with no prior bot expenses, **When** they sign in successfully, **Then** they see an empty-state message (not an error).
4. **Given** a signed-in user, **When** their session expires or they sign out, **Then** expense data is no longer visible until they sign in again.

---

### User Story 2 - View personal expense list (Priority: P1)

A signed-in user sees their personal expenses in a mobile-friendly, paginated list ordered by expense date (newest first). Each row shows date, description, amount in yen, and category name in the user's preferred language where translations exist.

**Why this priority**: Core MVP value — visibility into expenses already logged via the bot.

**Independent Test**: Log expenses via the bot in 1:1 chat, sign into the dashboard, and verify the list matches stored records (excluding soft-deleted items).

**Acceptance Scenarios**:

1. **Given** a user with at least one personal expense logged via the bot, **When** they open the dashboard with personal ledger selected, **Then** they see those expenses with date, description, amount, and category.
2. **Given** more expenses than one page holds, **When** the user scrolls or taps "load more", **Then** additional rows load without duplicating prior rows.
3. **Given** an expense was soft-deleted via bot reply-edit, **When** the user views the list, **Then** that expense does not appear.
4. **Given** the user's bot language preference is English, **When** they view the dashboard, **Then** UI chrome (labels, buttons, empty states) appears in English; category names follow available translations or fall back to Japanese taxonomy labels.

---

### User Story 3 - Switch between personal and group ledgers (Priority: P1)

A signed-in user who has interacted with the bot in group or room chats can switch the dashboard context from their personal ledger to a shared group or room ledger. Only ledgers where the user is a known prior interactor (same rule as bot-side group membership tracking) appear in the switcher.

**Why this priority**: Group shared expenses are a core bot feature; the dashboard must reflect the same tenancy model.

**Independent Test**: Log expenses in a group via two members, sign in as one member, switch to that group tenant, and see shared expenses.

**Acceptance Scenarios**:

1. **Given** user A has logged expenses in a LINE group via the bot, **When** user A opens the dashboard and selects that group from the tenant switcher, **Then** they see all non-deleted expenses for that group's shared ledger.
2. **Given** user A has only personal expenses (no group interaction), **When** they open the tenant switcher, **Then** only the personal ledger option is available.
3. **Given** user B is in a group but has never sent a bot-handled message there, **When** user B signs in, **Then** that group does not appear in their tenant switcher.
4. **Given** the user switches from personal to group ledger, **When** the list reloads, **Then** only expenses for the selected tenant are shown.

---

### User Story 4 - Open dashboard from bot rich menu (Priority: P2)

A LINE bot user can open the expense dashboard from a rich menu item on the bot's chat screen, landing in LIFF or the dashboard URL without manually typing a link.

**Why this priority**: Primary discovery path for mobile-first LINE users; not blocking core list functionality.

**Independent Test**: Tap the rich menu item in a 1:1 chat with the bot and confirm the dashboard opens and authenticates.

**Acceptance Scenarios**:

1. **Given** the bot rich menu is configured, **When** a user taps the dashboard menu item in a 1:1 chat, **Then** the mobile dashboard opens in the LINE in-app browser.
2. **Given** the user is not yet signed in, **When** they arrive via rich menu, **Then** LIFF or LINE Login completes and they reach the expense list.

---

### Edge Cases

- User signs in with a LINE account that has never used the bot: show friendly empty state, not a permission error.
- User belongs to many groups: tenant switcher remains usable on small screens (scroll or compact selector).
- Network failure while loading expenses: show retry affordance; do not expose raw error codes.
- Session valid but RLS returns no rows for a tampered tenant ID: show empty or forbidden state without leaking other users' data.
- Very long descriptions: truncate or wrap without breaking mobile layout.
- Expenses stored with non-JPY currency: hide from MVP list or show with a clear "unsupported currency" note (implementation choice documented in plan).

## Requirements

### Functional Requirements

- **FR-001**: The system MUST authenticate users via LINE Login (browser) and LIFF (in-app) and bind each session to exactly one LINE `userId`.
- **FR-002**: The system MUST link authenticated sessions to existing expense rows using `line_user_id` / `tenant_id` without requiring users to re-register.
- **FR-003**: The system MUST show a paginated, read-only list of expenses for the selected tenant, newest expense date first.
- **FR-004**: Each list row MUST display expense date, description, amount formatted as JPY, and category label.
- **FR-005**: The system MUST exclude soft-deleted expenses from the list.
- **FR-006**: The system MUST allow switching between the user's personal ledger (`tenant_type=user`) and any group or room ledger where the user is recorded as a prior interactor.
- **FR-007**: The system MUST NOT expose expenses from tenants the user is not authorized to view.
- **FR-008**: The system MUST NOT allow create, update, or delete of expenses from the web in MVP.
- **FR-009**: The dashboard UI MUST support Japanese, English, and Simplified Chinese for interface strings, consistent with bot language codes (`ja`, `en`, `zh`).
- **FR-010**: The bot MUST expose a rich menu entry that opens the dashboard URL for signed-in or sign-in-ready users.
- **FR-011**: The dashboard MUST be optimized for mobile-first layouts (readable on phone-width viewports without horizontal scrolling for primary content).
- **FR-012**: Service credentials with full database access MUST NOT be exposed to the browser.

### Key Entities

- **Authenticated user**: A person signed in via LINE; identified by LINE `userId`, linked to a Supabase Auth account for session management.
- **Tenant (ledger scope)**: Personal (`user` + LINE user ID) or shared (`group` / `room` + chat ID); matches the bot's expense tenancy model.
- **Expense (read view)**: A logged spending record with date, description, amount, currency, category, tenant scope, and optional soft-delete timestamp.
- **Tenant membership**: Association between a LINE user and a shared group/room ledger, derived from prior bot interaction in that chat.
- **Language preference**: User's preferred UI language (`ja`, `en`, `zh`), sourced from existing bot preference storage when available.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A user can sign in with LINE and see their first page of personal expenses in under 60 seconds on a typical mobile connection.
- **SC-002**: 100% of expenses shown in the dashboard belong to a tenant the signed-in user is authorized to view (zero cross-user data leakage in acceptance testing).
- **SC-003**: Users can switch between personal and at least one group ledger in under three taps after sign-in.
- **SC-004**: Paginated loading returns the next page within 3 seconds on a typical mobile connection for ledgers up to 1,000 active rows.
- **SC-005**: At least 90% of pilot users who tap the rich menu item reach the expense list without manual URL entry.

## Assumptions

- Users already log expenses through the existing LINE bot; the dashboard is a read mirror, not a new logging channel.
- LINE Login uses a **dedicated LINE Login channel** (LIFF cannot be added to Messaging API channels); Messaging API bot channel is separate. Both must be under the **same provider** so user IDs match.
- `tenant_chat_members` (maintained by the bot on inbound messages) is the authoritative list of which shared ledgers a user may access on the web.
- JPY is the only currency shown in MVP; most household users log yen amounts.
- Bot language preference in `user_language_preferences` is used when present; otherwise UI defaults to Japanese.
- Hosting on `*.vercel.app` is acceptable for MVP; HTTPS is provided by the platform.
- Supabase project `https://nyuenufldaqsjybjhawl.supabase.co` remains the single data store.

## Dependencies

- Existing expense schema and `v_expenses_enriched` view (features 004, 005, 006).
- `tenant_chat_members` from feature 007 for shared-ledger eligibility.
- `user_language_preferences` from feature 005/006 for locale selection.
- LINE Developers Console access to enable Login, LIFF app, callback URLs, and rich menu.
- Vercel project linked to the `web/` app in this repository.
