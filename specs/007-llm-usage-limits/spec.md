# Feature Specification: Per-User LLM Usage Limits

**Feature Branch**: `007-llm-usage-limits`

**Created**: 2026-06-12

**Status**: Draft

**Input**: Constrain user usage on LLM with per-user tracking (lifetime and monthly), payload size limits, multi-level message rate limits, and group chat quota pooling where a member may draw from other members' remaining quota after exhausting their own.

## Clarifications

### Session 2026-06-12

- Q: What is one "usage unit"? → A: **One LLM invocation** — each distinct call to the language model (intent check, receipt parse, categorization, reply-edit interpretation, etc.) counts as one usage event.
- Q: Do failed or rejected LLM calls count? → A: **No** — usage is recorded only after a successful LLM response is received; payload rejections and rate-limit blocks do not consume quota.
- Q: Do non-LLM paths count (deterministic text parse)? → A: **No** — only messages that actually invoke the LLM consume usage credits and count toward rate limits.
- Q: Monthly reset timezone? → A: **Asia/Tokyo (JST)** — monthly counters reset at the start of each calendar month in JST, consistent with expense dating.
- Q: Group quota pooling selection? → A: **Random eligible member** — when the sender has no remaining personal quota, the system randomly selects another group/room member who still has quota and charges that usage to them.
- Q: Monthly LLM quota per user? → A: **Free tier (all users in v1)** — **300** successful LLM invocations per calendar month (JST), plus a separate cap of **100 receipt analyses** per month (receipt analysis counts toward the 300 total).
- Q: Who can donate quota in group pooling? → A: **Prior interactors in that chat** — only users who have previously sent a bot-handled message in the same group/room are eligible donors.
- Q: Rate limits when quota is pooled? → A: **Sender rate limits, donor monthly quota** — the sender must be under per-minute and per-day message limits; the donor must have remaining monthly quota (and receipt-analysis sub-cap when applicable).
- Q: Do intent-check LLM calls on non-expense messages count? → A: **Count fully** — successful intent checks consume monthly total quota and sender rate limits; they do not consume the receipt-analysis sub-cap.
- Q: Receipt-analysis pooling in groups? → A: **Allow receipt pooling** — when the sender lacks receipt-analysis headroom, an eligible donor must have both total quota and receipt-analysis headroom; receipt usage charges the donor's receipt-analysis counter.

## Out of Scope (this feature)

- Paid subscription tiers, billing, or payment integration (tier **infrastructure** is in scope; only the **free** tier is active in v1)
- Admin web dashboard for quota management (configuration may use environment defaults only in v1)
- Token-weighted pricing or per-model differential costs
- Blocking LINE platform spam at the transport layer (only bot-side LLM usage is governed)
- Quota pooling in 1:1 personal chats
- Notifying users which group member's quota was consumed when pooling occurs
- Historical usage analytics export or charts

## User Scenarios & Testing

### User Story 1 - Per-user usage tracking (Priority: P1)

Each LINE user has their LLM usage recorded so operators can understand consumption and enforce fair limits. Every successful LLM call is attributed to a LINE user and stored with lifetime total and current-month count.

**Why this priority**: Without durable tracking, rate limits and quotas cannot be enforced or audited.

**Independent Test**: Process several expense messages for one user that trigger LLM calls, then verify stored totals match the number of successful invocations and that the monthly counter increments within the current JST month.

**Acceptance Scenarios**:

1. **Given** user A logs a receipt that triggers three successful LLM calls (intent, vision parse, categorization), **When** processing completes, **Then** user A's lifetime usage increases by 3, current-month usage increases by 3, and current-month receipt-analysis usage increases by 1.
2. **Given** user A's message is rejected before any LLM call (payload too large), **When** the bot replies with a rejection message, **Then** user A's usage counters do not change.
3. **Given** the calendar month rolls over in JST, **When** user A makes their next LLM-backed request, **Then** current-month usage resets to reflect only the new month's activity while lifetime total continues accumulating.

---

### User Story 2 - Payload size limits (Priority: P1)

Users cannot send oversized content to the LLM. Unreasonably large text or images are rejected early with a clear, localized message before any LLM call is attempted.

**Why this priority**: Prevents abuse, runaway cost, and poor user experience from inputs that are unlikely to be legitimate expense messages.

**Independent Test**: Send text above the word limit and an image above the size limit; confirm immediate rejection without LLM usage increment.

**Acceptance Scenarios**:

1. **Given** a user sends a text message exceeding **1,000 words**, **When** the bot evaluates the message, **Then** the user receives a rejection explaining the text is too long and no LLM call is made.
2. **Given** a user sends a receipt image larger than **10 MB**, **When** the bot evaluates the image, **Then** the user receives a rejection explaining the image is too large and no LLM call is made.
3. **Given** a user sends a normal expense text under the limit (e.g., "ランチ 1200円"), **When** processing continues, **Then** payload validation passes and normal expense flow proceeds.

---

### User Story 3 - Multi-level message rate limits (Priority: P1)

Users are limited in how frequently they can trigger LLM-backed bot processing. Limits apply at multiple time windows so burst spam and sustained abuse are both constrained.

**Why this priority**: Protects service availability and cost even when individual messages are small.

**Independent Test**: Rapidly send LLM-triggering messages until minute limit is hit; verify blocking message; repeat across a day to verify daily cap.

**Acceptance Scenarios**:

1. **Given** a user has triggered **10 LLM-backed messages within the past minute**, **When** they send another message that would invoke the LLM, **Then** the bot rejects the request with a rate-limit message and does not call the LLM.
2. **Given** a user has triggered **100 LLM-backed messages within the past 24 hours**, **When** they send another LLM-backed message, **Then** the bot rejects the request with a daily-limit message and does not call the LLM.
3. **Given** a user's minute window has elapsed since their burst, **When** they send a new valid message, **Then** processing is allowed if they are still under the daily cap.
4. **Given** a message is handled entirely without LLM (deterministic parse), **When** it is processed, **Then** it does not count toward minute or daily LLM message limits or monthly quota.
5. **Given** a user sends a non-expense text message that triggers a successful intent-check LLM call and is rejected, **When** processing completes, **Then** the sender's monthly total quota and rate-limit counters increment by one message and one invocation, but receipt-analysis usage does not change.

---

### User Story 4 - Group quota pooling (Priority: P2)

In group or room chats, each member has personal LLM quota. When a member has exhausted their own quota but the group still needs to process a message, the system may consume another member's remaining quota at random.

**Why this priority**: Keeps group expense logging usable when one heavy user exhausts their allowance while others still have headroom.

**Independent Test**: Exhaust user A's monthly quota in a group, send another receipt from user A while user B still has quota; confirm success and that user B's usage increased (not user A's).

**Acceptance Scenarios**:

1. **Given** user A and user B are in the same group, user A has **no remaining monthly LLM quota** while user B does, and user A is under rate limits, **When** user A sends a receipt that requires LLM, **Then** the message is processed successfully and usage is charged to user B (randomly selected among eligible donors).
2. **Given** user A has remaining personal quota, **When** user A sends an LLM-backed message in a group, **Then** usage is charged only to user A (no pooling).
3. **Given** all group members have exhausted their monthly quota, **When** any member sends an LLM-backed message, **Then** the bot returns a usage-limit message and does not call the LLM.
4. **Given** only one member is in the group, **When** they exhaust their quota, **Then** pooling does not occur and further LLM-backed requests are rejected.
5. **Given** user A has exhausted monthly quota but user B can donate, and user A is over the per-minute or per-day rate limit, **When** user A sends an LLM-backed message, **Then** the bot rejects based on user A's rate limit without pooling or LLM invocation.
6. **Given** user A has exhausted their receipt-analysis cap but user B has receipt-analysis headroom and total quota, **When** user A sends a receipt image in the group, **Then** the receipt is processed and receipt-analysis usage is charged to user B along with other LLM invocations in that flow.

---

### User Story 5 - Clear limit feedback (Priority: P2)

When a user hits any limit (payload, rate, or quota), they receive an understandable reply in their preferred bot language explaining what happened and when they can try again when applicable.

**Why this priority**: Reduces confusion and support burden when limits trigger.

**Independent Test**: Trigger each limit type and verify distinct, localized messages.

**Acceptance Scenarios**:

1. **Given** a user hits the per-minute rate limit, **When** the bot replies, **Then** the message indicates they are sending too fast and should wait briefly.
2. **Given** a user hits the daily rate limit, **When** the bot replies, **Then** the message indicates the daily limit is reached.
3. **Given** a user hits monthly LLM quota or the receipt-analysis sub-cap (with no pool available), **When** the bot replies, **Then** the message indicates the relevant AI usage limit is reached for the month.

---

### Edge Cases

- What happens when an LLM call succeeds but downstream processing fails (e.g., database error)? Usage is still recorded — the model was invoked.
- What happens on LLM retry/fallback across models for one logical step? **One usage event** per logical bot operation step, not per model attempt.
- What happens when the same LINE webhook is redelivered? Idempotent message handling must not double-count usage for the same `source_message_id` and operation.
- What happens for reply-edits that invoke LLM interpretation? They count as LLM-backed messages and consume quota like new expense submissions.
- What happens if no prior interactors besides the sender exist in a group? Pooling cannot occur; the sender receives a usage-limit message when their own quota is exhausted.
- What happens for brand-new users with no usage history? They start at zero usage with full **free-tier** default limits.
- What happens when a user is under the 300/month total cap but has used 100 receipt analyses? Further receipt images are rejected with a receipt-analysis limit message; non-receipt LLM operations may still proceed if under the total cap.
- What happens when a user exhausts the 300/month total but has receipt-analysis headroom remaining? All LLM operations are blocked — the total cap is authoritative.
- What happens if random pool selection races when two members send simultaneously? Each usage event must charge exactly one user; concurrent updates must not overdraw quota below zero.
- What happens when a sender is under monthly quota but over rate limits during pooling? Rate limits block the request before pooling or LLM invocation; donor quota is not consumed.
- What happens when a user sends non-expense chat (e.g., "hello") that triggers intent LLM? The successful intent check counts as one LLM invocation and one LLM-backed message toward the sender's limits; no receipt-analysis credit is used.
- What happens when a sender has receipt-analysis cap exhausted but total quota remains, and no donor has receipt-analysis headroom? Receipt images are rejected with a receipt-analysis limit message; non-receipt LLM operations may still proceed on the sender's quota or via donors with total headroom only.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST persist every successful LLM invocation with attribution to exactly one LINE user ID.
- **FR-002**: The system MUST maintain per-user **lifetime** LLM usage count and **current calendar month (JST)** LLM usage count.
- **FR-003**: The system MUST enforce a maximum text payload of **1,000 words** before any LLM call for text-based input.
- **FR-004**: The system MUST enforce a maximum image payload of **10 MB** before any LLM call for image-based input.
- **FR-005**: The system MUST enforce a rate limit of **10 LLM-backed messages per sending user per rolling 60-second window** (always attributed to the message sender, not a quota donor).
- **FR-006**: The system MUST enforce a rate limit of **100 LLM-backed messages per sending user per rolling 24-hour window** (always attributed to the message sender, not a quota donor).
- **FR-007**: The system MUST support **user tiers** with per-tier limits; in v1 every user is assigned the **free** tier and no tier upgrade path is exposed.
- **FR-007a**: The free tier MUST enforce a **monthly LLM usage quota of 300 successful invocations per user** (configurable without code changes in v1 via deployment configuration).
- **FR-007b**: The free tier MUST enforce a separate **monthly receipt-analysis cap of 100 successful invocations per user**; each receipt-analysis invocation also counts toward FR-007a.
- **FR-007c**: Receipt-analysis invocations are defined as successful LLM vision parses of receipt images (not intent checks, categorization, or reply-edit interpretation on text).
- **FR-007d**: Successful intent-classification LLM calls MUST count toward monthly total quota (FR-007a) and sender rate limits (FR-005, FR-006) even when the message is rejected as non-expense; they MUST NOT count toward the receipt-analysis sub-cap (FR-007b).
- **FR-008**: In group or room chats, when the sending user lacks remaining monthly quota (total and/or receipt-analysis sub-cap, as applicable), the system MUST attempt to charge a **randomly selected** eligible donor from the same chat who has the required remaining quota for the operation.
- **FR-008a**: Eligible donors MUST be LINE users who have previously sent at least one bot-handled message in the **same** group or room tenant; the sender is never an eligible donor for their own message.
- **FR-008b**: For receipt images, an eligible donor MUST have remaining receipt-analysis headroom (FR-007b) and total monthly headroom (FR-007a); successful receipt analysis MUST increment the donor's receipt-analysis counter.
- **FR-009**: Quota pooling MUST NOT apply in 1:1 personal chats.
- **FR-010**: Payload and rate-limit checks MUST occur **before** the first LLM call for that message.
- **FR-011**: Quota checks MUST occur **before** the first LLM call for that message; if pooling succeeds, subsequent LLM calls in the same message processing flow MUST charge the same pooled donor. Rate-limit checks MUST always evaluate the **sender**; monthly quota checks evaluate the sender first, then an eligible donor if pooling applies.
- **FR-012**: The system MUST NOT record usage for messages that are rejected by payload, rate, or quota checks.
- **FR-013**: Limit-exceeded replies MUST be localized (Japanese, English, Chinese) consistent with existing bot reply language behavior.
- **FR-014**: Usage records MUST be queryable per user for lifetime total and current-month total to support enforcement and future reporting.

### Key Entities

- **LLM Usage Event**: A single successful language-model invocation; attributes to one LINE user, timestamp (UTC stored, JST interpreted for monthly buckets), operation type (e.g., intent, receipt analysis, categorize, reply-edit), and source message identifier when available.
- **User Tier**: Named limit profile (e.g., `free`); v1 assigns `free` to all users; limits are read from tier configuration.
- **User Usage Summary**: Per LINE user — lifetime invocation count, current-month invocation count (JST month), current-month receipt-analysis count (JST month), assigned tier, last updated timestamp.
- **Rate Limit State**: Per LINE user rolling counters for 60-second and 24-hour LLM-backed message windows, always keyed to the **sender** of each inbound message.
- **Quota Pool Context**: For a group/room chat, the set of member LINE user IDs who have previously interacted with the bot in that tenant and still have remaining monthly quota (total and receipt-analysis sub-cap when applicable) to donate when the sender is exhausted.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of successful LLM invocations in production are attributed to a user in persistent storage within the same request lifecycle.
- **SC-002**: 0% of oversize text (>1,000 words) or images (>10 MB) reach the LLM (verified by test scenarios).
- **SC-003**: A single user cannot trigger more than 10 LLM-backed bot responses in any 60-second window under normal operation.
- **SC-004**: A single user cannot trigger more than 100 LLM-backed bot responses in any 24-hour window under normal operation.
- **SC-005**: When a group member with exhausted quota sends a receipt and another member has quota, at least 95% of test runs result in successful processing with quota charged to a donor member.
- **SC-006**: Users who hit a limit receive a reply within 3 seconds without an LLM call (pre-check path).
- **SC-007**: Monthly usage counters (total and receipt-analysis) reset correctly at JST month boundary in automated tests.
- **SC-008**: Free-tier users cannot exceed 100 receipt analyses in a JST calendar month even if their total monthly invocation count is below 300.
- **SC-009**: When a group sender lacks receipt-analysis headroom and an eligible donor has headroom, receipt processing succeeds with usage charged to the donor in at least 95% of test runs.

## Assumptions

- LINE user ID is the stable identity for quota, rate limits, and usage tracking in both 1:1 and group/room chats.
- All users are on the **free** tier in v1; tier infrastructure exists so paid or elevated tiers can be added later without redesigning metering.
- Free-tier monthly quota is **300 LLM invocations** with a **100 receipt-analysis** sub-cap; sufficient for typical personal expense tracking (~3 receipts/day at the analysis cap); operators can raise per-tier limits via configuration later.
- "Message" for rate limiting means one inbound user message that triggers at least one LLM call (not one LLM call per se for rate windows — a single receipt may invoke multiple LLM steps but counts as **one message** toward minute/daily message limits).
- Group membership for pooling is limited to users who have **previously sent a bot-handled message in the same group/room tenant**; no separate LINE membership sync in v1.
- Random donor selection uses uniform random choice among members with remaining quota excluding the sender.
- Existing provider-level quota errors (e.g., API-wide rate limits) remain handled separately; this feature governs **per-user** fair use on top of provider limits.
- Configuration defaults are acceptable for v1; self-service quota purchase is out of scope.

## Common Patterns Considered

The following industry patterns informed this specification (adopted, adapted, or deferred):

| Pattern | Application in this feature |
|--------|------------------------------|
| **Metering (count-based)** | One credit per successful LLM invocation; simple to explain and enforce. Token-weighted metering deferred. |
| **Multi-tier rate limiting** | Rolling minute + day windows for burst vs sustained abuse (token bucket / sliding window). |
| **Payload guardrails** | Reject absurd inputs before expensive operations (WAF-style size limits). |
| **Fail closed on quota** | No silent overage; user gets explicit limit message. |
| **Quota pooling / borrow** | Group chats allow borrowing another member's balance — uncommon but specified for shared household groups. |
| **Idempotent billing** | Same inbound message redelivery must not double-charge. |
| **Charge on success only** | Failed LLM calls do not bill — standard fair-use pattern. |
| **Localized denial responses** | Users understand *why* they were blocked and *when* to retry. |
| **Tiered plans (deferred activation)** | Tier model in scope; only **free** tier active in v1; paid tiers added later without changing metering shape. |
| **Deferred: admin override** | Manual quota grants — out of scope v1; use config defaults. |
