# Feature Specification: Product Monetization (Paid Tier)

**Feature Branch**: `cursor/japan-monetization-eff7`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "I want to monetize this product, tell me what will be the easiest way to link to a payment service. I’m in Japan and is personal now, I can apply 個人事業主 if that’s better."

## Recommended payment path (operator decision)

For a Japan-based **personal** operator of this LINE + web expense product, the easiest practical path is:

1. **Register as 個人事業主** (file 開業届 with the tax office). Major payment processors that accept Japan merchants expect a business identity; 個人事業主 is enough for v1 and is simpler than forming a 株式会社.
2. **Use a hosted checkout payment service that supports Japan cards and subscription billing** (assumed provider for planning: **Stripe Japan** — see Assumptions). Hosted checkout avoids building card forms or storing payment credentials.
3. **Sell a monthly paid plan from the existing signed-in web dashboard**, then update the user’s **usage tier** so the bot enforces higher LLM quotas already prepared by the usage-limits feature.
4. **Defer** in-app LINE Pay UI, convenience-store (コンビニ) settlement, and App Store / Google Play billing until after card subscription works.

Why this is easiest: one merchant application, minimal payment UI (redirect to hosted checkout + customer portal), identity already exists via LINE Login on the web app, and paid entitlement maps cleanly onto the existing free/paid **tier** model rather than inventing a new billing ledger for every bot message.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Subscribe to a paid plan from the web app (Priority: P1)

A signed-in user who is hitting free-tier usage limits wants more capacity. From the web dashboard they start a paid monthly plan, complete payment with a Japanese card (or other methods the chosen payment service offers in Japan), and return to the app with paid access active.

**Why this priority**: Without a working subscribe path, monetization does not exist.

**Independent Test**: As a signed-in free-tier user, complete the subscribe flow in a test/sandbox payment environment and verify the account shows paid status and elevated limits without using the bot.

**Acceptance Scenarios**:

1. **Given** a signed-in free-tier user, **When** they open the upgrade/subscribe entry point in the web app and confirm the paid plan, **Then** they are taken to a hosted payment checkout and can complete purchase without entering card details into this product’s own forms.
2. **Given** payment succeeds, **When** they return to the web app, **Then** their account shows an active paid plan and the elevated usage limits that paid status grants.
3. **Given** the user abandons or cancels checkout before paying, **When** they return to the web app, **Then** they remain on the free tier with no charge and no elevated limits.

---

### User Story 2 - Paid limits apply in the LINE bot (Priority: P1)

After subscribing, the same person continues using the LINE bot. Their monthly LLM and receipt-analysis limits follow the paid tier instead of the free tier, while rate limits and payload guards remain in force.

**Why this priority**: Revenue is justified by product value in the primary surface (LINE chat); web-only entitlement would not match how people use the product.

**Independent Test**: Set a test user to paid status, exhaust free-tier quota thresholds that would block a free user, and confirm bot requests still succeed until paid-tier limits are reached.

**Acceptance Scenarios**:

1. **Given** a user with an active paid plan, **When** they send LLM-backed expense messages within paid monthly quotas, **Then** the bot processes them normally even if usage exceeds free-tier monthly quotas.
2. **Given** a paid user exhausts their paid monthly quota, **When** they send another LLM-backed message in a 1:1 chat, **Then** they receive a clear limit message that explains the limit and points them to manage or wait for the next month (JST), without calling the LLM.
3. **Given** a free user who has not paid, **When** they hit free-tier monthly quotas, **Then** behavior remains as today (limit message; no silent overage).

---

### User Story 3 - Manage, cancel, or see billing status (Priority: P2)

A paid user can see that they are on a paid plan, when the current period renews, and can cancel or update payment details through a trusted billing portal without contacting the operator manually.

**Why this priority**: Reduces support burden and is required for trustworthy subscriptions, but subscribe + entitlement is the MVP core.

**Independent Test**: From the web app as a paid user, open manage-billing, cancel renewal in the sandbox portal, and verify access remains until period end then reverts to free.

**Acceptance Scenarios**:

1. **Given** an active paid user, **When** they open billing management from the web app, **Then** they can view plan status and open a hosted customer portal to update payment method or cancel.
2. **Given** a user cancels renewal, **When** the current paid period is still active, **Then** they keep paid limits until the period ends, after which they return to free-tier limits automatically.
3. **Given** a free user, **When** they view the upgrade area, **Then** they see that they are on the free plan and a clear call to subscribe (no bogus paid status).

---

### User Story 4 - Failed payment and expired access (Priority: P2)

If a renewal charge fails or paid access expires, the product stops granting paid limits and tells the user how to restore access, without corrupting expense data.

**Why this priority**: Protects revenue integrity and user trust; slightly secondary to first successful subscribe.

**Independent Test**: Simulate a failed renewal or expired subscription for a test user and confirm bot/web treat them as free while historical expenses remain intact.

**Acceptance Scenarios**:

1. **Given** a paid subscription becomes past-due or unpaid after renewal failure, **When** the payment service notifies the product, **Then** the user loses paid limits within a short, predictable window and sees a restore/update-payment prompt in the web app.
2. **Given** paid access ends, **When** the user continues using the bot under free limits, **Then** existing expenses, categories, budgets, and wish-list data remain available; only usage entitlements change.
3. **Given** the user successfully updates payment and the subscription becomes active again, **When** entitlement refreshes, **Then** paid limits are restored without requiring a new account.

---

### User Story 5 - Operator onboarding for Japan sole proprietorship (Priority: P3)

The operator (currently personal) can complete the minimum real-world steps to accept live payments as a Japan 個人事業主 and turn on live mode when ready.

**Why this priority**: Blocks live money but not product build against sandbox; documented as an operator checklist rather than end-user UX.

**Independent Test**: Operator completes sandbox end-to-end; live mode is gated until merchant verification and bank payout details are accepted by the payment service.

**Acceptance Scenarios**:

1. **Given** the operator has filed 開業届 and has a Japanese bank account, **When** they complete payment-service merchant onboarding for Japan, **Then** they can receive payouts for successful charges.
2. **Given** merchant verification is incomplete, **When** users attempt live checkout, **Then** live charges are not accepted (sandbox may still work for development).

---

### Edge Cases

- What happens if the payment service confirms success but the product fails to record paid status? The product MUST retry entitlement sync from payment events and MUST NOT leave the user charged without a recoverable way to activate paid access (support path or automatic reconciliation).
- What happens if the same user pays twice quickly? The product MUST NOT create two active paid entitlements that double-charge quotas or confuse cancellation; duplicate checkouts resolve to a single active subscription.
- What happens in group chats when only one member is paid? Paid limits apply to that member’s own quota; existing group quota-pooling rules still apply when a sender is exhausted — paid status does not silently buy unlimited group capacity for unpaid members.
- What happens if LINE Login identity and payment customer records drift? Entitlement MUST remain keyed to the signed-in LINE-linked account used by the web app and bot usage metering.
- What happens when the JST month resets while a subscription is active? Monthly usage counters reset per existing metering rules; subscription period is independent of the usage month unless the plan explicitly says otherwise.
- What happens offline / payment service outage during checkout? User remains free-tier; they can retry; no partial paid state from an incomplete checkout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST offer at least one **paid monthly plan** that a signed-in web user can purchase through a hosted payment checkout (no card data stored by this product).
- **FR-002**: Successful payment MUST activate a **paid usage tier** for that user so bot LLM monthly quotas exceed the free tier (exact paid quota values are operator-configurable; see Assumptions for v1 defaults).
- **FR-003**: The product MUST keep free-tier behavior unchanged for users without an active paid entitlement.
- **FR-004**: The product MUST reflect paid vs free status in the web app with a clear upgrade entry point and current plan summary.
- **FR-005**: The product MUST allow paid users to manage or cancel billing via a hosted customer portal linked from the web app.
- **FR-006**: The product MUST revoke or downgrade paid limits when the subscription is canceled at period end, unpaid, or otherwise no longer active, without deleting user expense or settings data.
- **FR-007**: The product MUST process payment lifecycle notifications (success, failure, cancel, renew) so entitlement stays consistent with the payment service’s source of truth.
- **FR-008**: Checkout and portal flows MUST work for users in Japan using at least ordinary Japanese-issued cards supported by the chosen payment service.
- **FR-009**: When a user hits a usage limit, bot and/or web messaging MUST distinguish free-tier exhaustion (with upgrade guidance) from paid-tier exhaustion (with wait-until-reset or manage-plan guidance).
- **FR-010**: Automated tests MUST cover subscribe entitlement activation, downgrade after cancel/expiry, and bot enforcement of paid vs free quotas without charging real money or mutating the live household production ledger.
- **FR-011**: Operator documentation MUST describe Japan 個人事業主 merchant setup, sandbox vs live mode, and the recommended payment service path for this product.

### Key Entities

- **Paid Plan**: A sellable monthly offering with display name, price, billing interval, and linked usage-tier profile (higher monthly LLM / receipt limits than free).
- **Subscription Entitlement**: The user’s current right to a paid tier — active, canceling-at-period-end, past-due, or inactive — tied to their LINE-linked account.
- **Payment Customer**: The billing identity at the external payment service for one signed-in user (not a separate end-user login).
- **Checkout Session**: A one-time hosted payment attempt that either activates entitlement or leaves the user on free.
- **Usage Tier Profile**: Named limit set (`free`, `paid`, …) already used by metering; monetization only assigns which profile a user gets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new signed-in user can complete sandbox subscribe and see paid status in the web app in under **3 minutes**.
- **SC-002**: Within **1 minute** of successful sandbox payment, the bot treats that user under paid monthly quotas (verified in automated or scripted checks).
- **SC-003**: After cancel-at-period-end in sandbox, **100%** of test users keep paid limits until period end and revert to free afterward without manual database edits.
- **SC-004**: **100%** of expense history remains intact across subscribe, cancel, and payment-failure downgrade scenarios in acceptance tests.
- **SC-005**: Free users who hit monthly limits receive upgrade guidance; paid users who hit paid limits receive manage/wait guidance — verified for Japanese and English reply languages already supported by the product.
- **SC-006**: Operator can run full subscribe → use bot → cancel cycle in sandbox **without** live merchant approval; live mode requires only merchant onboarding completion, not a product rewrite.

## Assumptions

- **Easiest payment link for this operator**: Register as **個人事業主**, then use **Stripe Japan** (hosted checkout + customer billing portal + automatic payment-status updates into the product). This is the default planning assumption because it minimizes custom payment UI, supports Japan cards and sole-proprietor merchants, and fits the existing signed-in web dashboard + LINE Login identity. Alternatives (e.g. Pay.jp) remain acceptable if Stripe onboarding is blocked; the product requirements stay provider-agnostic.
- **Why 個人事業主 vs staying “personal”**: Pure personal / hobby settlement is poorly supported by mainstream card processors for ongoing SaaS charges. 開業届 is the low-friction legal step that unlocks merchant accounts and proper tax treatment; a 株式会社 is unnecessary for v1.
- **What is sold in v1**: A single monthly **Personal Paid** subscription that raises the subscriber’s LLM monthly total and receipt-analysis caps (building on the existing free-tier metering). No lifetime license, no per-message micropayments, no family/group seat packs in v1.
- **v1 paid quota defaults** (operator-configurable): **1,500** successful LLM invocations / JST month and **500** receipt analyses / JST month (receipt analyses also count toward the total). Free tier remains **300** / **100** as today.
- **v1 price default** (operator-configurable, displayed in JPY): on the order of **¥480–¥980 / month** — exact sticker price chosen at launch; product must not hard-require a single hardcoded consumer price in business rules beyond “monthly paid plan”.
- **Identity**: Web LINE Login account is the same person as the LINE bot user for entitlement; one paid subscription covers that LINE user ID’s personal metering.
- **Group chats**: Unchanged pooling rules; monetization does not sell shared household seats in v1.
- **Out of scope for v1**: Konbini / carrier billing as primary path, LINE Pay in-chat checkout, App Store/Play billing, invoices for corporations, VAT/tax-engine localization beyond what the payment service provides, refund self-serve UI beyond the payment portal, annual plans, trials longer than what the payment service supports with minimal config, and advertising-based monetization.
- **Existing systems reused**: Free-tier usage limits, tier assignment hooks, web auth, and bot limit messages — monetization activates paid tier assignment rather than replacing metering.
- **Compliance**: Operator is responsible for 開業届, tax filing, and payment-service KYC; the product provides documentation and technical integration only.

## Out of Scope

- Building a custom card-entry form or storing raw card numbers
- Selling access to unrelated features (persona packs, separate wish-list SKUs) in v1
- Changing LINE Messaging API pricing or LINE Official Account plans
- Multi-currency pricing outside JPY for v1
- Admin console for manually granting complimentary paid tiers (may be added later as support tooling)
