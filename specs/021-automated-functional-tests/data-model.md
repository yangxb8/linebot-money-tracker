# Data Model: Automated Functional Testing

**Feature**: 021-automated-functional-tests

This feature does **not** introduce persisted production schema. The “model” is the catalog of automated scenarios, verification lanes, and simulated identities used only inside tests.

## Conceptual model

```text
VerificationLane
  ├── PR_FAST (mocked auth/data/externals)  ← v1 delivery
  └── DEEP_SCHEDULED (optional later; isolated remote tenant)

FunctionalScenario ──belongs_to──► VerificationLane
       │
       ├── surface: bot | web_api | web_browser
       ├── given / when / then
       └── asserts: reply_contract | http_status | side_effects | ui_redirect

TestIdentity (simulated)
  └── used_by web_api + web_browser scenarios in PR_FAST
```

## Entity: VerificationLane

| Attribute | Values / notes |
| --------- | -------------- |
| id | `pr_fast` \| `deep_scheduled` |
| auth | mocked (`pr_fast`) \| remote test tenant (`deep_scheduled`, deferred) |
| data stores | in-memory / mocked (`pr_fast`) \| isolated remote DB (deferred) |
| externals | Gemini/LINE mocked (`pr_fast`); may be real in deep lane |
| CI trigger | every PR/push (`pr_fast`); schedule only (deep, out of v1) |
| merge gate | hard fail if suite red (`pr_fast`); deep never required for merge in v1 |

## Entity: FunctionalScenario

| Attribute | Notes |
| --------- | ----- |
| id | Stable slug, e.g. `bot.wish.accept` |
| surface | `bot` \| `web_api` \| `web_browser` |
| priority | P1/P2 for v1; deferred marked out of suite |
| given | Preconditions (unsigned request, pending confirmation, no session, …) |
| when | Action (POST `/callback`, route handler call, browser navigation) |
| then | Observable outcomes (status, reply shape, mock call counts, redirect) |
| lane | Always `pr_fast` for v1 scenarios |

### v1 catalog (required)

| id | surface | then (summary) |
| -- | ------- | -------------- |
| `bot.webhook.unsigned` | bot | HTTP 400; no `reply_message` |
| `bot.expense.text_confirm` | bot | Confirmation-style reply; expense/pending side effects asserted |
| `bot.expense.reply_edit` | bot | Amount updated; reply reflects change |
| `bot.wish.accept` | bot | Wish item created; no expense insert |
| `bot.wish.decline` | bot | Neither wish nor expense created |
| `web.browser.auth_gate` | web_browser | Protected URL → `/login` |
| `web.browser.signed_in_smoke` | web_browser | One app page loads without login bounce |
| `web.api.expenses_overview` | web_api | 200 + ledger or empty |
| `web.api.wish_list_mutate` | web_api | Create/update then read reflects change |
| `web.api.settings_bot_behavior` | web_api | Save then read reflects values |
| `web.api.budgets` | web_api | Read/update succeeds with expected state |
| `web.api.categories` | web_api | Create/update then read reflects change |
| `web.api.unauthorized` | web_api | 401 without mocked user (at least one representative route) |

### Explicitly out of v1 catalog

| id | reason |
| -- | ------ |
| `bot.expense.image` | FR-017 deferred |
| `bot.wish.image_text` | FR-017 deferred |
| `web.api.periodic_*` | FR-015 deferred |
| `deep.bot_to_web` | FR-012 optional later |

## Entity: TestIdentity (simulated)

| Attribute | Notes |
| --------- | ----- |
| line_user_id / auth user id | Fixed fake id in mocks |
| tenant_type / tenant_id | Personal ledger defaults for web mocks |
| session | Fake `getUser()` return; no real cookies against live Supabase in PR lane |
| permissions | Full access to own tenant only (mirrors `assertTenantAccess` happy path) |

## Entity: TestExpansionObligation (process)

| Attribute | Notes |
| --------- | ----- |
| applies_to | New user-facing features |
| required_artifacts | Spec/plan/tasks include test-expansion; PR updates suites when behavior changes |
| enforcement | Soft: `AGENTS.md` + constitution + review; Hard: CI red if suites fail |
| non_requirement | Diff need not touch test files for infra/docs-only PRs |

## Validation rules

- PR_FAST scenarios MUST NOT call production household project or real Gemini/LINE APIs.
- Browser scenarios MUST NOT exceed auth gate + one signed-in page in v1.
- Bot reply assertions SHOULD prefer stable structural cues (presence of confirmation markers, side-effect mocks) over full persona-rendered strings.
- Scenario ids in contracts SHOULD match test names or markers for traceability.

## State transitions

Not applicable to production data. Scenario lifecycle is documentation-only: `planned` → `implemented` → `ci_green`.
