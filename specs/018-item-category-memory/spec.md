# Feature Specification: Item-Level Category Memory for Receipts

**Feature Branch**: `cursor/item-category-memory-e56a`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: Improve tenant category memory (013/014) so receipt/image flows from mixed-goods stores can map different products to different categories. Prefer accuracy over LLM skip rate. Apply item-level memory to all receipt/image parses (1+ lines); keep merchant-only memory for short text. Remember categories per item (normalized product name), prefer store+item then item-only. Reply-edit of one line updates only that item’s memory. Item-only writes only on explicit correction; merchant memory is soft prior on classify miss; backfill store+item only.

## Clarifications

### Session 2026-07-14

- Q: Primary goal for v1? → A: **Fix mixed-store receipts (accuracy first)**
- Q: When memory conflicts at one store? → A: **Keep multiple category memories; match by item description**
- Q: What should “remember” for a store? → A: **Per (store, item/description) mappings**
- Q: Scope of new behavior? → A: **Multi-item receipt/image flows only**
- Q: Reply-edit category change for one mixed-receipt line? → A: **Update only that item signature (not the whole store)**
- Q: Lookup preference when both store+item and item-only memories exist? → A: **Prefer (store, item); fall back to item-only; then classify without memory**
- Q: Single-line receipt images — item memory or merchant-only? → A: **Any receipt/image parse (1+ lines) uses item-memory rules; text stays merchant-only**
- Q: When to write item-only (cross-store) memory? → A: **Store+item on LLM/silent; item-only only on explicit user category correction**
- Q: Cold start when no item memory but merchant memory exists? → A: **Per-line classify with merchant remembered category as soft prior/hint only (not hard assignment)**
- Q: Backfill item memory from historical expenses? → A: **Backfill store+item from history; never backfill item-only**
- Q: High-confidence item memory — must skip classify? → A: **MUST skip at high confidence (parity with 013, e.g. weight ≥ 1.0)**

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Mixed-store receipt gets different categories per line (Priority: P1)

A user photographs a home-center receipt with a plant pot and toilet paper. The bot assigns gardening/plants to the pot and daily necessities to the toilet paper in the same confirmation (e.g. separate category subtotals), instead of forcing one store-wide category.

**Why this priority**: This is the observed failure mode (島忠ホームズ → all 植物) and the core accuracy goal.

**Independent Test**: Log a two-item receipt from a mixed store with distinct product names and no prior conflicting item memories; confirm each line receives a category appropriate to the product; confirm both categories can appear in one confirmation.

**Acceptance Scenarios**:

1. **Given** a multi-item receipt with two distinct product descriptions at the same store and no usable item memory for those lines, **When** expenses are categorized, **Then** each line may receive a different category even if merchant-only memory exists for that store (merchant memory is at most a soft hint, not a hard skip).
2. **Given** the same mixed-store receipt, **When** confirmation is shown, **Then** category subtotals (or per-item detail, if enabled) reflect those distinct categories.
3. **Given** a short text expense (not a receipt/image parse), **When** categorized, **Then** existing merchant-only memory behavior is unchanged.
4. **Given** a single-line receipt/image parse with a valid item key, **When** categorized, **Then** item-memory rules apply (not merchant-only hard-skip for that line).

---

### User Story 2 — Learned item memory skips re-asking for the same product (Priority: P1)

After the user corrects (or silently accepts) “toilet paper at store X” to daily necessities, a later receipt line with the same normalized item at that store is categorized the same way without needing another correction.

**Why this priority**: Memory must still reduce wrong guesses and corrections for repeat products; accuracy fix must not remove learning.

**Independent Test**: Correct one receipt line’s category for a product at store X; log another multi-item receipt containing the same normalized product at store X; verify that line uses the remembered category.

**Acceptance Scenarios**:

1. **Given** tenant memory for (store X, item “トイレ用紙”) → daily necessities with high confidence, **When** a new multi-item receipt includes that item at store X, **Then** that line is assigned daily necessities from memory.
2. **Given** high-confidence memory for (store X, item A) and (store X, item B) with different categories, **When** both appear on one receipt, **Then** each line uses its own remembered category.
3. **Given** memory for (store X, item A) only, **When** a different product at store X appears, **Then** that other product does not inherit item A’s category via store-only memory.

---

### User Story 3 — Cross-store reuse of item memory (Priority: P2)

A user **explicitly corrects** toilet paper to daily necessities at one chain. Later, a receipt at another store has a matching normalized item name. The bot reuses the item-only memory when no store-specific memory exists for that pair. Uncorrected LLM guesses at a store do **not** create or overwrite cross-store item-only memory.

**Why this priority**: Speeds learning for commodity goods across chains for trusted corrections only, without letting noisy LLM seeds thrash shared item keys.

**Independent Test**: Explicitly correct an item category at store A; log matching item at store B with no (B, item) memory; verify category comes from item-only memory. Separately, LLM-only classify (no correction) at store A must not create item-only memory that affects store B.

**Acceptance Scenarios**:

1. **Given** item-only memory for normalized item I → category C created by user correction, and no (store B, I) memory, **When** a receipt/image at store B includes I, **Then** the line is assigned category C.
2. **Given** both (store B, I) → category C1 and item-only I → category C2, **When** categorizing I at store B, **Then** C1 wins (store+item preferred).
3. **Given** no store+item and no item-only memory for I, **When** categorizing, **Then** the system classifies without item memory (normal classify path).
4. **Given** only an LLM seed (no user category correction) for item I at store A, **When** the same item appears at store B, **Then** item-only memory MUST NOT apply from that LLM seed alone.

---

### User Story 4 — Reply-edit teaches only that item (Priority: P1)

On a multi-item confirmation, the user changes only line 2’s category. Memory for that item signature is updated; other lines’ memories and any legacy store-wide mapping are not overwritten by that edit.

**Why this priority**: Prevents one correction (e.g. toilet paper → 日用品) from poisoning future plant purchases at the same store.

**Independent Test**: Two-line confirmation at store X; reply-edit category on line 2 only; verify only line 2’s item memory updates; later receipt plant line does not receive line 2’s category from that edit alone.

**Acceptance Scenarios**:

1. **Given** a multi-item confirmation, **When** the user reply-edits category for a single line, **Then** only that line’s item memory (store+item and/or item signature as applicable) is updated.
2. **Given** that correction, **When** a later receipt includes a different product at the same store, **Then** that other product is not forced to the corrected category solely because of the prior line’s edit.
3. **Given** a category reply-edit on a multi-item receipt line, **When** memory is updated, **Then** the update does not replace memory for unrelated items at that store.

---

### User Story 5 — Text expenses keep merchant memory (Priority: P2)

A user logs `スターバックス ラテ 580円` as text. Merchant-level memory still applies as in today’s 013 behavior.

**Why this priority**: Preserve the high-value skip/learning path for cafes, transit, and other single-merchant text logs.

**Independent Test**: Correct Starbucks once via text flow; log Starbucks again as text; verify remembered merchant category still applies. A single-line receipt photo of a Starbucks cup still uses item-memory rules (not merchant hard-skip alone).

**Acceptance Scenarios**:

1. **Given** merchant-only memory for Starbucks with high confidence, **When** user logs a Starbucks text expense, **Then** category comes from merchant memory (unchanged from 013).
2. **Given** only item-level receipt memories exist for a product name, **When** user logs a short text expense that is not a multi-item receipt, **Then** text path does not require item-level keys to function (merchant / existing path remains valid).

---

### Edge Cases

- Product description is generic or empty after normalization (e.g. “商品”, “不明”) — treat as no item key; do not write item memory; classify without item memory.
- OCR/vision yields noisy SKU suffixes (`W2 A`, pack sizes) — normalization SHOULD collapse obvious pack/size/model noise so the same product can rematch; if still unique, miss memory and classify normally.
- Store name missing on a multi-item receipt — use item-only memory when available; otherwise classify without item memory.
- Same normalized item already remembered under two categories via conflicting corrections — last writer wins for that exact memory key (same as 013 conflict rule, but per item key).
- Legacy high-confidence merchant-only memory for a mixed store — MUST NOT hard-assign receipt/image lines; at most a soft classify hint (FR-007a).
- Single-line receipt image (one product) — MUST use item-memory rules when an item key exists (same receipt/image path as multi-line); MUST NOT regress merchant text-path behavior for non-receipt messages.
- User corrects category to `unknown` for an item — memory MAY store unknown; rematch may skip re-classify (same product tradeoff as 013).

## Requirements *(mandatory)*

### Functional Requirements

#### Scope

- **FR-001**: System MUST apply item-level category memory on **all receipt/image** expense flows (one or more line items from a receipt parse, including single-line receipt photos).
- **FR-002**: System MUST retain existing **merchant-only** category memory behavior for short **text** logs that are not receipt/image parses (feature 013 path).
- **FR-003**: For receipt/image flows with multiple lines, system MUST NOT assign every line the same category solely because they share a store name or merchant key.

#### Item identity

- **FR-004**: System MUST derive a normalized **item key** from each line’s product description (after cleaning register/SKU noise) for memory lookup and write on receipt/image flows.
- **FR-005**: System MUST skip item-memory read and write when the item key is missing or generic (denylist / too short / empty after normalize).
- **FR-006**: When a receipt-level store name is present, system MUST also form a **store+item** memory identity from (normalized store/merchant key, item key).

#### Lookup order (receipt/image)

- **FR-007**: On receipt/image categorization, for each line, system MUST lookup memory in this order: (1) store+item, (2) item-only, (3) no item memory → classify per line (category LLM / existing classify path). Merchant-only hard-skip MUST NOT assign the category for receipt/image lines.
- **FR-007a**: When step (3) classify runs and a merchant-only memory category exists for the store, system MUST pass that category to the classifier only as a **soft prior / hint**. The hint MUST NOT force the line to that category; different lines on the same receipt may still receive different categories.
- **FR-008**: When store+item and item-only both exist with different categories, store+item MUST win.
- **FR-009**: When a store+item or item-only memory hit has high confidence (**weight ≥ 1.0**, same threshold as 013) and the stored category remains valid for the tenant, system MUST skip category LLM for that line and use the remembered category. Confirmation labeling remains the same “guess” style as today (no special “remembered” label required). Alternatives MAY be empty on such hits.

#### Learning / writes

- **FR-010**: On category LLM (or equivalent) classification of a receipt/image line with a valid item key and known store, system MUST upsert **store+item** memory only (LLM seed / weight philosophy as 013). LLM classification MUST NOT create or update **item-only** memory.
- **FR-010a**: On silent acceptance for a rematched store+item identity, system MAY strengthen **store+item** confidence only — MUST NOT write or strengthen item-only from silent confirm alone.
- **FR-011**: On reply-edit (or bulk) **explicit category correction** for a receipt/image line with a valid item key, system MUST upsert **store+item** (when store known) **and** **item-only** for that item key to the corrected category at high confidence. Updates apply only to that line’s item identity — NOT other items at the store, and NOT store-wide merchant-only memory from a single-line edit.
- **FR-012**: When store is unknown on a receipt/image line, LLM/silent paths still MUST NOT write item-only; item-only is written only via explicit category correction (FR-011) when the item key is valid.
- **FR-013**: Bulk category edit that intentionally changes multiple lines MUST apply FR-011 per affected line.

#### Legacy merchant memory coexistence

- **FR-014**: Existing merchant-only memory rows remain valid for text (non-receipt) flows (FR-002).
- **FR-015**: For receipt/image flows, legacy merchant-only high-confidence mappings MUST NOT hard-assign line categories; item memory hits (FR-007–FR-009) take precedence, and on classify miss merchant memory is soft-prior only (FR-007a).

#### Backfill

- **FR-018**: A one-time (idempotent) backfill MUST seed **store+item** memory from historical receipt/image expense lines that have a usable store/merchant key, a valid item key, and a final category.
- **FR-019**: Backfill MUST NOT create or update **item-only** memory (item-only remains correction-only per FR-011).
- **FR-020**: Backfill conflict policy for the same store+item key: last writer by expense recency wins (aligned with 013 last-writer semantics), with confidence capped consistently with 013 backfill practice.

#### Tenancy & UX

- **FR-016**: Item memory MUST remain scoped by tenant (personal or group/room ledger), same isolation as 013.
- **FR-017**: Confirmation UX MUST continue to support distinct categories per line (subtotals / optional item detail) without requiring new user-facing memory management UI in v1.

### Key Entities *(include if feature involves data)*

- **Item key**: Normalized product identity derived from a receipt line description (noise-stripped, pack/size collapsed where defined).
- **Store+item memory**: Per-tenant learned mapping from (store/merchant key, item key) → category, with confidence/weight and provenance.
- **Item-only memory**: Per-tenant learned mapping from item key → category for cross-store reuse; created/updated only by explicit user category correction, used when no store+item hit exists.
- **Merchant-only memory** (existing): Per-tenant store/merchant → category mapping used for text (non-receipt) flows.
- **Receipt line expense**: Existing per-line expense with description, optional store name, and category guess.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a representative mixed-store multi-item receipt fixture (at least two product types that belong in different categories), including when merchant-only memory exists for that store, the bot assigns **different categories to those lines in ≥90%** of automated evaluation runs (or scripted golden cases), without store-wide hard assignment.
- **SC-002**: After one explicit category correction for a receipt line’s item at store X, a later matching (store X, item) line is categorized correctly on first guess **≥80%** of the time (parity with 013 SC-004, scoped to item identity), and high-confidence rematches skip category LLM (**≥95%** skip rate when weight ≥ 1.0 in metering).
- **SC-003**: When item-only memory exists from an **explicit user correction** (no store+item for the new store), a matching item at a different store reuses that category in **≥70%** of golden cases with stable normalized names. LLM-only seeds MUST NOT produce that cross-store reuse.
- **SC-004**: Category reply-edits that change only one line of a multi-item confirmation update memory such that a **different** product at the same store is **not** forced to the edited category in follow-up golden cases (**0 false carry-over** in the test suite).
- **SC-005**: Short text merchant memory regression suite (Starbucks/Uber-style) remains at **≥95%** of pre-change pass rate.
- **SC-006**: After backfill, historical receipt lines with extractable store+item identity seed store+item memory for **≥50%** of eligible lines in a sample cohort; item-only row count attributable to backfill is **0**.

## Assumptions

- Features 013 (tenant category memory) and 014 (receipt store name) remain the baseline; this feature extends them rather than replacing text merchant memory.
- Receipt/image flow means one or more expense line items from a receipt parse (vision or future OCR receipt path), including single-line receipt photos; free-text messages are not receipt/image flows.
- Item-key normalization can be deterministic rules first (NFKC, noise strip, drop common size/pack suffixes); embedding/fuzzy match is out of scope for v1.
- Weight / confidence thresholds **mirror 013**: LLM seed gradual; silent confirm strengthens store+item; explicit correction sets high confidence; **skip category LLM when weight ≥ 1.0** for applicable item-memory hits (FR-009).
- No web UI to browse or edit item memory in v1 (same as 013).
- Confirmation presentation (category subtotals / optional item details from 017) already supports multiple categories; this feature does not redesign reply format.
- Cross-store item reuse is desirable for commodity goods after explicit correction — overrides remain via preferring store+item (FR-008). LLM seeds do not populate item-only memory.
- Historical expenses used for store+item backfill are those attributable to receipt/image logging (e.g. image source / persisted store_name), not free-text shorthand.

## Out of Scope

- Embedding / fuzzy product matching across dissimilar OCR strings
- Web dashboard for viewing or editing memory rows
- Changing the category taxonomy itself
- Applying item-level memory as the primary path for free-text expenses (non-receipt messages)
- Automatic decay/expiry of memory rows
- Global (cross-tenant) item or merchant memory sharing
- Backfilling item-only memory from history

## Dependencies

- **013** — tenant category memory, weight model, reply-edit learning signals, prior backfill patterns
- **014** — receipt-level store name propagated to line items
- **004** — per-line expense persistence
- **005 / 008** — reply-edit and bulk category change
- **017** — confirmation display of multi-category subtotals
