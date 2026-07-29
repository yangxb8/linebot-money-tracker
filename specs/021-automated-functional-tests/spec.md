# Feature Specification: Automated Functional Testing

**Feature Branch**: `021-automated-functional-tests`

**Created**: 2026-07-29

**Status**: Draft

**Input**: User description: "Summarize automatic functionality testing recommendations (bot webhook/API tests, harness scenario tests, web API tests, browser end-to-end smoke) into a spec; also add agent instructions so any feature going forward must expand the test suite."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Catch bot regressions before merge (Priority: P1)

As a maintainer, when someone changes LINE bot behavior, automated checks verify the main chat flows still work end-to-end at the product boundary (inbound message → reply), without needing a live LINE account or paid AI calls on every change review.

**Why this priority**: Bot regressions directly affect household expense logging; today most coverage is unit-level, so broken webhook contracts or confirmation flows can slip through.

**Independent Test**: Run the project’s automated bot functional suite with mock credentials only; confirm expense log, reply-edit, wish-list confirm/decline, and webhook rejection/success paths pass or fail clearly.

**Acceptance Scenarios**:

1. **Given** an unauthorized or unsigned inbound webhook request, **When** the automated bot suite runs, **Then** the request is rejected and no reply is sent.
2. **Given** a valid inbound text expense message (mocked AI and storage), **When** the suite runs, **Then** the system produces a confirmation-style reply and the expected persistence/pending side effects are asserted.
3. **Given** a prior confirmation message, **When** the suite simulates a reply-edit with a new amount, **Then** the expense is updated and the reply reflects the change.
4. **Given** a wish-list intent followed by yes or no, **When** the suite runs both paths, **Then** yes creates a wish item without logging an expense, and no creates neither.

---

### User Story 2 - Catch web dashboard regressions before merge (Priority: P1)

As a maintainer, when someone changes the web dashboard, automated checks verify that signed-in users can still complete core money-management tasks (view expenses, manage wish list, budgets, categories, settings), and that signed-out users cannot access protected areas.

**Why this priority**: The web app is the second product surface; unit tests on helpers do not prove pages and server actions behave correctly for users.

**Independent Test**: Run the automated web functional suite against a disposable authenticated session (or equivalent test identity); confirm protected-route denial and at least one happy path each for expenses, wish list, and settings persistence.

**Acceptance Scenarios**:

1. **Given** a visitor with no session, **When** they open a protected dashboard URL, **Then** they are sent to sign-in and no private data is shown.
2. **Given** a signed-in test user, **When** they open the expense overview, **Then** the page loads successfully and shows the user’s ledger content (or empty state).
3. **Given** a signed-in test user, **When** they add or update a wish-list item through the UI or documented product API surface, **Then** the change is visible on reload.
4. **Given** a signed-in test user, **When** they save bot-behavior settings, **Then** reloading settings shows the saved values.

---

### User Story 3 - Continuous checks on every change review (Priority: P2)

As a maintainer, every proposed change automatically runs the fast functional suites (bot + web) alongside existing unit checks, using only mock or dedicated test credentials—not production secrets—so reviews get a clear pass/fail signal.

**Why this priority**: Suites that are not in the default change pipeline will rot; CI is what makes functional coverage durable.

**Independent Test**: Open a sample change that does not alter product behavior; confirm the pipeline runs bot unit tests, web unit tests, and the new functional suites, all green without real LINE/AI production credentials.

**Acceptance Scenarios**:

1. **Given** a normal pull request, **When** continuous checks run, **Then** bot unit tests, web unit tests/lint, and bot+web functional suites all execute and report status.
2. **Given** a deliberately broken functional assertion, **When** continuous checks run, **Then** the pipeline fails and blocks confident merge.

---

### User Story 4 - Future features must grow the suite (Priority: P1)

As a product owner, whenever a new feature is specified or implemented, the work includes expanding automated tests for that feature’s primary user flows, and coding agents are instructed to treat missing test expansion as incomplete work.

**Why this priority**: One-time suite investment fails if new features skip tests; agent policy is the enforcement mechanism in this repo’s workflow.

**Independent Test**: Review agent instruction docs and a sample new-feature checklist: each requires explicit test-suite expansion; a feature PR without new/updated functional or unit coverage for its primary flows is considered incomplete.

**Acceptance Scenarios**:

1. **Given** agent instructions for this repository, **When** an agent implements any new feature, **Then** the instructions require adding or extending automated tests for that feature’s primary acceptance scenarios before calling the work done.
2. **Given** a new feature specification or task list, **When** planning/implementation artifacts are produced, **Then** they include explicit tasks or requirements to extend the automated test suite (not only manual quickstart steps).
3. **Given** a pull request for a user-facing change with no corresponding test updates, **When** reviewed against project policy, **Then** it is treated as incomplete relative to the constitution and agent rules.

---

### User Story 5 - Optional deeper confidence (nightly / cross-surface) (Priority: P3)

As a maintainer, optionally on a schedule (not every PR), a small set of deeper checks can exercise real AI analysis and/or prove that a bot-logged item appears in the web ledger for a dedicated test household.

**Why this priority**: High confidence but costly/flaky; valuable after the fast suites exist, not required for the first release of this feature.

**Independent Test**: When enabled, a scheduled run completes a short real-AI or bot→web smoke pack against an isolated test tenant and reports results without touching production household data.

**Acceptance Scenarios**:

1. **Given** scheduled deep checks are configured, **When** they run against the isolated test tenant, **Then** at least one bot-logged expense or wish item is observable from the web product surface for that tenant.
2. **Given** deep checks are not configured, **When** PR continuous checks run, **Then** they still pass using only mock/fast suites (deep checks remain optional).

---

### Edge Cases

- What happens when external AI or messaging credentials are missing in CI? Fast suites MUST still run using mocks; they MUST NOT require production secrets.
- How does the system handle flaky browser or network timing in UI checks? Suites MUST prefer stable assertions (visible outcomes, persisted data) and keep UI smoke paths few.
- What if a feature only changes copy/i18n? Tests MUST still assert the user-visible outcome for the affected language/persona path, or explicitly extend existing reply-contract checks.
- What if bot and web share a ledger change? Prefer a functional test on at least one surface in the PR suite; cross-surface proof may live in optional scheduled checks.
- How are destructive tests isolated? Functional tests MUST use mock stores or a dedicated test tenant—never the live household production data used by real users.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide an automated bot functional suite that verifies inbound message handling at the product boundary, including unauthorized request rejection and successful reply generation for core flows.
- **FR-002**: The bot functional suite MUST cover at least: text expense confirmation, reply-based amount edit, wish-list accept, and wish-list decline.
- **FR-003**: The bot functional suite MUST run without live messaging-provider accounts and without paid AI calls (external dependencies mocked or stubbed).
- **FR-004**: The project MUST provide an automated web functional suite that verifies unauthenticated access is denied for protected areas and that authenticated users can complete core dashboard tasks.
- **FR-005**: The web functional suite MUST cover at least: expense overview load, wish-list create/update visibility, and bot-behavior settings save/reload.
- **FR-006**: Web functional checks that require sign-in MUST use a dedicated test identity or seeded session—not interactive personal LINE login during CI.
- **FR-007**: Pull-request continuous checks MUST run existing bot unit tests, web unit tests (and lint), and the new bot + web functional suites.
- **FR-008**: Pull-request continuous checks MUST NOT depend on production household data or production messaging/AI credentials.
- **FR-009**: Repository agent instructions MUST state that every new user-facing feature is incomplete until the automated test suite is expanded to cover that feature’s primary acceptance scenarios.
- **FR-010**: Feature planning and task artifacts for future work MUST include explicit test-expansion work (unit and/or functional as appropriate to the change), not only manual verification notes.
- **FR-011**: Existing unit and SQL policy tests MUST remain part of the default verification path; this feature adds functional coverage rather than replacing unit tests.
- **FR-012**: Optional scheduled deep checks (real AI and/or bot→web cross-surface) MAY be added after the fast suites; they MUST use an isolated test tenant and MUST NOT be required for PR merge in the first delivery of this feature.
- **FR-013**: Functional suites MUST produce clear pass/fail output suitable for CI and local developer runs documented in a quickstart for this feature.

### Key Entities

- **Functional scenario**: A named user journey (e.g., “wish-list accept”) with given/when/then expectations executable by automation.
- **Test identity**: An isolated signed-in user/tenant used only for automated web checks.
- **Verification lane**: A grouping of checks—fast PR lane (mocked) vs optional deep lane (scheduled/real services).
- **Test-expansion obligation**: The rule that each new feature adds or updates scenarios covering its primary acceptance criteria.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Maintainers can verify the four core bot journeys (expense confirm, reply-edit, wish accept, wish decline) with a single automated command in under 5 minutes on a standard developer machine or CI runner, without live messaging or paid AI.
- **SC-002**: Maintainers can verify protected-route denial plus expense overview, wish-list update, and settings save/reload with automated web checks in under 10 minutes without interactive personal login.
- **SC-003**: 100% of pull requests run the fast bot and web functional suites in continuous checks; a failing functional scenario blocks a green pipeline.
- **SC-004**: After this feature ships, 100% of subsequent user-facing feature specs/task lists include explicit automated test-expansion items, enforced via updated agent instructions.
- **SC-005**: Zero automated functional tests write to or mutate the real household production ledger used by end users.
- **SC-006**: At least 80% of the manual quickstart flows currently documented for expense logging, reply-edit, and wish-list add/confirm have a corresponding automated functional scenario in the fast suite.

## Assumptions

- Existing bot and web unit tests remain the first line of defense; this feature layers product-boundary functional coverage on top.
- Mocking external AI and messaging in the PR lane is acceptable; exact reply wording may assert stable structural/contract cues where persona/i18n makes full-string matches brittle.
- Web authentication in automation will reuse the project’s existing session model via a seeded test identity rather than automating the full LINE Login UI in v1.
- Browser-level UI smoke is in scope for the web suite but kept to a small number of happy paths; deeper edge cases stay in unit/API-level checks.
- Nightly real-AI and cross-surface packs are optional (P3) and may ship after the fast suites.
- “Expand the test suite” for a feature means adding or updating automated tests for that feature’s primary acceptance scenarios; pure refactors with no behavior change may only require existing suites to stay green.
- Agent-facing policy will live in `AGENTS.md` (and remain consistent with the project constitution’s test-first principle).
