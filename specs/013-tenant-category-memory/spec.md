# Feature Specification: Tenant Category Memory

**Feature Branch**: `013-tenant-category-memory`

**Created**: 2026-06-24

**Status**: Draft

**Input**: Improve LINE bot category-guess accuracy by remembering merchant→category mappings per tenant (personal or group/room ledger). Record LLM classifications and user corrections with normalized merchant keys. Skip LLM when memory confidence is high. Backfill from existing expenses. No web UI. Merchant aliases seeded from YAML. Receipt `store_name` extraction deferred to feature 014.

## Clarifications

### Session 2026-06-24 (planning)

- Q: Memory scope? → A: **Per tenant** (`tenant_type` + `tenant_id`). Different tenants may map the same merchant to different categories.
- Q: Merchant extraction? → A: **LLM** extracts `merchant_name` from expense description (or receipt context when available).
- Q: Skip-LLM threshold? → A: **weight ≥ 1.0**
- Q: LLM seed weight? → A: **+0.25** per LLM classification when writing memory
- Q: Web UI for memory? → A: **No** — bot-only learning via logging and reply-edits
- Q: Historical data? → A: **Yes** — backfill memory from existing expenses on deploy
- Q: Confirmation label when from memory? → A: **Keep same** — still show `カテゴリ（推測）` / `Category (guess)` / `类别（推测）`
- Q: Conflicting corrections within tenant? → A: **Last writer wins** silently (overwrite category + reset weight to 1.0)
- Q: Merchant alias dictionary? → A: **YAML seed only** in repo; no runtime UI. Seed should cover major Japanese merchants (see appendix).
- Q: Receipt store vs line items? → A: **Deferred** — receipt parser `store_name` is a separate feature (014). Until then, merchant is extracted from description via LLM.

## Out of Scope (this feature)

- Web dashboard to view or edit category memory
- Cross-tenant (global) memory sharing
- Embedding / fuzzy merchant matching
- Memory expiry or automatic decay
- Per-user memory rows within a shared group (tenant-level only; last correction within tenant wins)
- Receipt-level `store_name` field (see `specs/014-receipt-store-name/spec.md`)
- Changes to category taxonomy structure (010)
- Budget impact in confirmation messages

## User Scenarios & Testing

### User Story 1 — Repeat merchant auto-categorized (Priority: P1)

A user logs an expense at a merchant they corrected before (e.g. `スターバックス ラテ 580円`). The bot assigns the remembered category without calling the category LLM, and the confirmation looks the same as a fresh guess.

**Why this priority**: Core value — fewer wrong guesses and faster responses for recurring merchants.

**Independent Test**: Correct Starbucks to `food.dining` once; log another Starbucks expense; verify same category assigned and no category LLM call in usage logs.

**Acceptance Scenarios**:

1. **Given** tenant memory for merchant key `starbucks` with weight ≥ 1.0 mapping to `food.dining`, **When** user logs `スターバックス 渋谷店 ラテ`, **Then** category is `food.dining` without category LLM invocation.
2. **Given** memory hit, **When** confirmation is sent, **Then** label remains `カテゴリ（推測）` (or localized equivalent) — not a new “remembered” label.
3. **Given** tenant has customized category names (010), **When** memory returns code `food.dining`, **Then** confirmation displays tenant `name_ja` path.

---

### User Story 2 — User correction teaches tenant memory (Priority: P1)

A user reply-edits a wrong category on a confirmation message. The bot updates the expense and upserts tenant memory so the same merchant is classified correctly next time.

**Why this priority**: User corrections are the highest-trust signal.

**Independent Test**: Log expense at unknown merchant; reply-edit category to `transport.transit`; log same merchant again; verify auto-category without LLM.

**Acceptance Scenarios**:

1. **Given** a logged expense with merchant `Uber`, **When** user changes category to `transport.transit` via reply-edit, **Then** memory for `(tenant, uber)` is set to `transport.transit` with weight 1.0 and source `user_correction`.
2. **Given** memory already exists for merchant with a different category, **When** another group member corrects to a new category, **Then** memory is overwritten silently (last writer wins within tenant).
3. **Given** correction on multi-item confirmation, **When** only item 2 category changes, **Then** memory is updated only for that item's extracted merchant.

---

### User Story 3 — Silent confirmation strengthens memory (Priority: P2)

A user logs an expense, does not change the category (may edit amount or simply accept), and logs the same merchant again later. The second lookup has higher confidence.

**Why this priority**: Rewards correct guesses without requiring explicit confirmation action.

**Independent Test**: Log merchant first time (LLM guess); do not category-edit; log same merchant again; verify weight increased and second log may skip LLM once weight ≥ 1.0.

**Acceptance Scenarios**:

1. **Given** first log with LLM guess `food.grocery` and weight 0.25, **When** user does not category-edit the confirmation, **Then** memory weight increases by 0.5 (silent confirm) → total 0.75.
2. **Given** weight 0.75 after one silent confirm, **When** user logs same merchant again without category-edit, **Then** weight reaches 1.25 and subsequent logs skip category LLM.
3. **Given** user changes amount but not category, **When** confirmation completes, **Then** silent confirm still applies.

---

### User Story 4 — Generic descriptions always use LLM (Priority: P1)

A user logs a vague expense (`食費 3000円`, `買い物`, `payment`) with no identifiable merchant. The bot always calls the category LLM and does not read or write merchant memory.

**Why this priority**: Prevents bad global mappings from generic text.

**Independent Test**: Log `食費 5000円` twice with different intended categories; verify LLM called each time and no memory row for generic key.

**Acceptance Scenarios**:

1. **Given** description with no extractable merchant (LLM returns null/empty or generic token), **When** expense is categorized, **Then** category LLM is always invoked.
2. **Given** generic description, **When** user corrects category, **Then** memory is not created or updated.
3. **Given** merchant extractable, **When** description also contains generic words, **Then** merchant memory path is used.

---

### User Story 5 — Backfill from historical expenses (Priority: P2)

On first deploy, the system seeds tenant memory from existing expense rows so repeat merchants benefit immediately.

**Why this priority**: Day-one accuracy without waiting for new corrections.

**Independent Test**: Run backfill migration/script against staging DB with known expenses; verify memory rows created per tenant with weights derived from final categories.

**Acceptance Scenarios**:

1. **Given** historical expenses with extractable merchants and final `category_code`, **When** backfill runs, **Then** one memory row per `(tenant_type, tenant_id, merchant_key)` is upserted.
2. **Given** multiple expenses for same merchant with same final category, **When** backfill runs, **Then** weight reflects count (e.g. silent-confirm equivalent) capped at 1.0 for backfill seed.
3. **Given** same merchant mapped to different categories in history, **When** backfill runs, **Then** most recent expense's category wins (last writer by `expense_date` / `created_at`).

---

### User Story 6 — Group ledger shared memory (Priority: P1)

Two members of a group ledger log expenses at the same merchant. The first member's correction applies to the second member's future logs in that group.

**Why this priority**: Group tenant is a first-class ledger; memory must be tenant-scoped not user-scoped.

**Independent Test**: Member A corrects `ドン・キホーテ` in group G; Member B logs `ドンキ` in group G; verify B gets A's category.

**Acceptance Scenarios**:

1. **Given** memory in group tenant G, **When** any member logs matching merchant, **Then** memory applies.
2. **Given** personal tenant P and group tenant G, **When** user corrected merchant in P, **Then** G does not inherit P's memory (isolated tenants).

---

## Requirements

### Functional Requirements

#### Memory storage

- **FR-001**: System MUST store merchant→category memory scoped by `(tenant_type, tenant_id, merchant_key)` where `tenant_type` ∈ {`user`, `group`, `room`}.
- **FR-002**: Each memory row MUST include: `merchant_key` (normalized), `display_merchant` (latest raw name for logs), `category_code` (tenant-valid taxonomy code), `weight` (numeric), `hit_count`, `last_source` (`llm` | `user_correction` | `silent_confirm` | `backfill`), `sample_description`, `updated_at`.
- **FR-003**: `(tenant_type, tenant_id, merchant_key)` MUST be unique.

#### Merchant extraction and normalization

- **FR-004**: System MUST use an LLM call to extract `merchant_name` from expense description (and amount/currency context) before category lookup. This MAY share the expense-parse LLM turn when parsing new messages, or be a dedicated lightweight call under `llm_operation_scope('merchant_extract')`.
- **FR-005**: System MUST normalize extracted merchant to `merchant_key` via deterministic rules: NFKC, lowercase ASCII keys, strip branch/address suffixes, apply YAML alias map (`data/merchant_aliases_ja.yaml`).
- **FR-006**: System MUST treat descriptions as **generic** (skip memory read/write) when merchant extraction returns empty or matches a built-in generic denylist (e.g. `食費`, `買い物`, `payment`, `expense`, `不明`, single-character tokens).
- **FR-007**: YAML alias seed MUST cover major Japanese merchant chains across convenience, supermarket, drugstore, dining, transport, and delivery (minimum set in [appendix-merchant-alias-seed.md](./appendix-merchant-alias-seed.md)).

#### Category classification flow

- **FR-008**: On new expense, after merchant extraction: if `merchant_key` present, lookup tenant memory; if `weight ≥ 1.0`, use `category_code` as guess **without** category LLM call.
- **FR-009**: If memory miss or `weight < 1.0`, invoke existing `classify_expense` category LLM; on success, upsert memory with `+0.25` weight delta and `last_source=llm` (do not exceed skip threshold from LLM alone).
- **FR-010**: Memory `category_code` MUST be validated via tenant `resolve_code()` before use; invalid codes fall back to category LLM.
- **FR-011**: Confirmation UI MUST NOT distinguish memory vs LLM guesses (same guess label and alternatives format). When memory hit, alternatives MAY be empty or populated from taxonomy siblings (implementation choice; default: empty alternatives on memory hit).

#### Learning from user actions

- **FR-012**: On explicit category correction via reply-edit (including bulk category change), MUST upsert memory for extractable merchant: set `category_code` to chosen code, `weight=1.0`, `last_source=user_correction`.
- **FR-013**: On confirmation completed without category change (final category equals original guess), MUST add `+0.5` weight (`silent_confirm`) for extractable merchant if memory row exists or create row if missing.
- **FR-014**: Explicit correction MUST overwrite prior category for same `(tenant, merchant_key)` silently (no user notification).
- **FR-015**: Category delete/soft-delete without category change MUST NOT trigger silent confirm for that item.

#### Analytics fields

- **FR-016**: System MUST persist on each expense: `category_guess_code` (first assigned code) and `category_source` (`memory` | `llm`) for accuracy metrics.
- **FR-017**: System MUST support computing per-tenant: **% expenses not category reply-edited** and **% expenses with guess `unknown`** over a rolling window (SQL view or RPC acceptable).

#### Backfill

- **FR-018**: One-time backfill job MUST scan existing `expenses` joined to tenant scope, extract merchant (LLM batch or rule fallback for backfill only), and seed memory with `last_source=backfill` and weight up to 1.0 based on historical consistency.
- **FR-019**: Backfill MUST be idempotent (safe to re-run).

#### Non-functional

- **FR-020**: Memory lookup MUST complete before category LLM decision; added latency acceptable per product owner.
- **FR-021**: Bot service role writes memory; no web RLS required for v1 (no web UI).

### Key Entities

- **Category merchant memory**: Per-tenant learned mapping from normalized merchant key to taxonomy category code, with accumulated weight and provenance.
- **Merchant alias**: Static YAML entry mapping variant spellings (Japanese, katakana, half-width, English) to canonical `merchant_key`.
- **Expense category provenance**: Denormalized guess code and source on expense row for analytics.

### Edge Cases

- Merchant extraction returns a chain name but user uses highly custom tenant category — memory stores taxonomy `code`; display uses tenant names.
- User corrects to `unknown` — memory MAY store `unknown` but `weight ≥ 1.0` still skips LLM (always returns unknown). Product accepts this; user can correct again.
- Same merchant, different categories for different amounts — v1 ignores amount; merchant-only key (accepted limitation).
- Tenant has no customized taxonomy yet — memory codes resolve against global template.
- LLM merchant extraction fails — fall through to category LLM only; no memory write.
- Periodic/cron-posted expenses — same memory path as user-logged expenses.
- Multi-item receipt: each line item gets its own merchant extraction from line description until 014 provides shared `store_name`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Within 30 days of deploy, **≥20% relative reduction** in category reply-edits (compared to 30-day pre-deploy baseline) for tenants with ≥10 logged expenses.
- **SC-002**: Within 30 days of deploy, **% unknown at guess time** decreases by **≥15% relative** vs pre-deploy baseline (same tenant cohort).
- **SC-003**: For merchants with memory `weight ≥ 1.0`, **≥95%** of classifications skip category LLM (verified via usage metering).
- **SC-004**: Repeat merchant (same `merchant_key`, same tenant) logs category correctly on first guess **≥80%** of the time after one explicit user correction.
- **SC-005**: Backfill seeds memory for **≥50%** of historical expenses where merchant is extractable (non-generic descriptions).

## Assumptions

- Merchant extraction LLM cost is acceptable at log time (one additional scoped call or merged parse field).
- Last-writer-wins within a group tenant is acceptable for conflicting corrections (no per-user override).
- Weight model: explicit correction = 1.0; silent confirm = +0.5; LLM seed = +0.25; skip threshold = 1.0.
- Until feature 014, line-item descriptions on multi-line receipts may yield per-line merchant keys rather than store-level keys.
- Generic denylist is maintained in code; alias list is maintained in YAML.
- Memory is not migrated when tenant categories are deleted/transferred (010) — orphaned codes fall back to LLM via `resolve_code` unknown handling; optional cleanup deferred.

## Dependencies

- **004** — expense storage, `classify_expense`
- **005** — reply-edit category persistence
- **006** — group/room tenant scope
- **010** — per-tenant taxonomy `resolve_code`
- **014** (future) — receipt `store_name` for improved merchant key on receipts

## Appendix

- [Merchant alias seed requirements](./appendix-merchant-alias-seed.md)
