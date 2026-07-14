# Feature Specification: Item-Level Category Memory for Receipts

**Feature Branch**: `cursor/item-category-memory-e56a`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: Improve tenant category memory (013/014) so multi-item receipts from mixed-goods stores (home centers, variety stores) can map different products to different categories. Prefer accuracy over LLM skip rate. Scope new behavior to multi-item receipt/image flows only. Remember categories per item (normalized product name), scoped preferentially by store, with cross-store item reuse as fallback. Reply-edit of one line updates only that item’s memory, not the whole store. Keep existing merchant-only memory for short text / single-item logs.

## Clarifications

### Session 2026-07-14

- Q: Primary goal for v1? → A: **Fix mixed-store receipts (accuracy first)**
- Q: When memory conflicts at one store? → A: **Keep multiple category memories; match by item description**
- Q: What should “remember” for a store? → A: **Per (store, item/description) mappings**
- Q: Scope of new behavior? → A: **Multi-item receipt/image flows only**
- Q: Reply-edit category change for one mixed-receipt line? → A: **Update only that item signature (not the whole store)**
- Q: Lookup preference when both store+item and item-only memories exist? → A: **Prefer (store, item); fall back to item-only; then classify without memory**

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Mixed-store receipt gets different categories per line (Priority: P1)

A user photographs a home-center receipt with a plant pot and toilet paper. The bot assigns gardening/plants to the pot and daily necessities to the toilet paper in the same confirmation (e.g. separate category subtotals), instead of forcing one store-wide category.

**Why this priority**: This is the observed failure mode (島忠ホームズ → all 植物) and the core accuracy goal.

**Independent Test**: Log a two-item receipt from a mixed store with distinct product names and no prior conflicting item memories; confirm each line receives a category appropriate to the product; confirm both categories can appear in one confirmation.

**Acceptance Scenarios**:

1. **Given** a multi-item receipt with two distinct product descriptions at the same store, **When** expenses are categorized, **Then** each line may receive a different category (not a single store-forced category for all lines).
2. **Given** the same mixed-store receipt, **When** confirmation is shown, **Then** category subtotals (or per-item detail, if enabled) reflect those distinct categories.
3. **Given** a short text / single-item expense (not a multi-item receipt), **When** categorized, **Then** existing merchant-only memory behavior is unchanged.

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

A user corrected toilet paper to daily necessities at one chain. Later, a receipt at another store has a matching normalized item name. The bot reuses the item-only memory when no store-specific memory exists for that pair.

**Why this priority**: Speeds learning for commodity goods across chains without forcing one category for entire stores.

**Independent Test**: Create item memory via correction at store A; log matching item at store B with no (B, item) memory; verify category comes from item-only memory.

**Acceptance Scenarios**:

1. **Given** item-only memory for normalized item I → category C, and no (store B, I) memory, **When** a multi-item receipt at store B includes I, **Then** the line is assigned category C.
2. **Given** both (store B, I) → category C1 and item-only I → category C2, **When** categorizing I at store B, **Then** C1 wins (store+item preferred).
3. **Given** no store+item and no item-only memory for I, **When** categorizing, **Then** the system classifies without item memory (normal classify path).

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

**Independent Test**: Correct Starbucks once via text flow; log Starbucks again as text; verify remembered merchant category still applies.

**Acceptance Scenarios**:

1. **Given** merchant-only memory for Starbucks with high confidence, **When** user logs a Starbucks text expense, **Then** category comes from merchant memory (unchanged from 013).
2. **Given** only item-level receipt memories exist for a product name, **When** user logs a short text expense that is not a multi-item receipt, **Then** text path does not require item-level keys to function (merchant / existing path remains valid).

---

### Edge Cases

- Product description is generic or empty after normalization (e.g. “商品”, “不明”) — treat as no item key; do not write item memory; classify without item memory.
- OCR/vision yields noisy SKU suffixes (`W2 A`, pack sizes) — normalization SHOULD collapse obvious pack/size/model noise so the same product can rematch; if still unique, miss memory and classify normally.
- Store name missing on a multi-item receipt — use item-only memory when available; otherwise classify without item memory.
- Same normalized item already remembered under two categories via conflicting corrections — last writer wins for that exact memory key (same as 013 conflict rule, but per item key).
- Legacy high-confidence merchant-only memory for a mixed store — MUST NOT force all receipt lines to that single category once this feature is active for multi-item receipts.
- Single-line receipt image (one product) — MAY use item memory when an item key exists; MUST NOT regress merchant text-path behavior for non-receipt messages.
- User corrects category to `unknown` for an item — memory MAY store unknown; rematch may skip re-classify (same product tradeoff as 013).

## Requirements *(mandatory)*

### Functional Requirements

#### Scope

- **FR-001**: System MUST apply item-level category memory on **multi-item receipt/image** expense flows (multiple line items from one parse).
- **FR-002**: System MUST retain existing **merchant-only** category memory behavior for short text / non-multi-item receipt logs (feature 013 path), unless FR-001 applies.
- **FR-003**: For multi-item receipt flows, system MUST NOT assign every line the same category solely because they share a store name or merchant key.

#### Item identity

- **FR-004**: System MUST derive a normalized **item key** from each line’s product description (after cleaning register/SKU noise) for memory lookup and write on multi-item receipt flows.
- **FR-005**: System MUST skip item-memory read and write when the item key is missing or generic (denylist / too short / empty after normalize).
- **FR-006**: When a receipt-level store name is present, system MUST also form a **store+item** memory identity from (normalized store/merchant key, item key).

#### Lookup order (multi-item receipts)

- **FR-007**: On multi-item receipt categorization, for each line, system MUST lookup memory in this order: (1) store+item, (2) item-only, (3) no item memory → classify with existing non-item path (category LLM / other existing rules). Merchant-only hard-skip MUST NOT override this order for multi-item receipt lines.
- **FR-008**: When store+item and item-only both exist with different categories, store+item MUST win.
- **FR-009**: High-confidence item memory hits (store+item or item-only) MAY skip category re-classification for that line; confirmation labeling remains the same “guess” style as today (no special “remembered” label required).

#### Learning / writes

- **FR-010**: On category LLM (or equivalent) classification of a multi-item receipt line with a valid item key, system MUST upsert item memory (store+item when store known; item-only always when key valid) using the same confidence/weight philosophy as 013 (LLM seeds raise confidence gradually; explicit correction sets high confidence).
- **FR-011**: On reply-edit category change for a single multi-item confirmation line, system MUST update memory only for that line’s item identity (store+item and/or item-only as applicable) — NOT replace memory for other items at the store, and NOT rewrite store-wide merchant-only memory from that single-line edit.
- **FR-012**: Silent acceptance signals (no category change on a later rematch) MAY strengthen confidence for that item identity only.
- **FR-013**: Bulk category edit that intentionally changes multiple lines MUST update memory for each affected line’s item identity.

#### Legacy merchant memory coexistence

- **FR-014**: Existing merchant-only memory rows remain valid for text / single-item non-receipt flows (FR-002).
- **FR-015**: For multi-item receipt flows, legacy merchant-only high-confidence mappings MUST NOT force all lines to one category; item memory rules (FR-007–FR-009) take precedence for those lines.

#### Tenancy & UX

- **FR-016**: Item memory MUST remain scoped by tenant (personal or group/room ledger), same isolation as 013.
- **FR-017**: Confirmation UX MUST continue to support distinct categories per line (subtotals / optional item detail) without requiring new user-facing memory management UI in v1.

### Key Entities *(include if feature involves data)*

- **Item key**: Normalized product identity derived from a receipt line description (noise-stripped, pack/size collapsed where defined).
- **Store+item memory**: Per-tenant learned mapping from (store/merchant key, item key) → category, with confidence/weight and provenance.
- **Item-only memory**: Per-tenant learned mapping from item key → category for cross-store reuse when no store+item hit exists.
- **Merchant-only memory** (existing): Per-tenant store/merchant → category mapping used for text / non-multi-item flows.
- **Receipt line expense**: Existing per-line expense with description, optional store name, and category guess.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a representative mixed-store multi-item receipt fixture (at least two product types that belong in different categories), the bot assigns **different categories to those lines in ≥90%** of automated evaluation runs (or scripted golden cases), without requiring a store-wide single category.
- **SC-002**: After one explicit category correction for a receipt line’s item at store X, a later matching (store X, item) line is categorized correctly on first guess **≥80%** of the time (parity with 013 SC-004, scoped to item identity).
- **SC-003**: When only item-only memory exists (no store+item), a matching item at a different store reuses that category in **≥70%** of golden cases with stable normalized names.
- **SC-004**: Category reply-edits that change only one line of a multi-item confirmation update memory such that a **different** product at the same store is **not** forced to the edited category in follow-up golden cases (**0 false carry-over** in the test suite).
- **SC-005**: Short text / single-item merchant memory regression suite (Starbucks/Uber-style) remains at **≥95%** of pre-change pass rate.

## Assumptions

- Features 013 (tenant category memory) and 014 (receipt store name) remain the baseline; this feature extends them rather than replacing text merchant memory.
- Multi-item receipt/image means two or more expense line items from one receipt parse (vision or future OCR receipt path).
- Item-key normalization can be deterministic rules first (NFKC, noise strip, drop common size/pack suffixes); embedding/fuzzy match is out of scope for v1.
- Weight / confidence thresholds may mirror 013 (correction = high confidence; LLM seed gradual; silent confirm strengthens) unless planning finds a receipt-specific tuning need.
- No web UI to browse or edit item memory in v1 (same as 013).
- Confirmation presentation (category subtotals / optional item details from 017) already supports multiple categories; this feature does not redesign reply format.
- Cross-store item reuse is desirable for commodity goods even if rare store-specific overrides exist — those overrides are handled by preferring store+item (FR-008).

## Out of Scope

- Embedding / fuzzy product matching across dissimilar OCR strings
- Web dashboard for viewing or editing memory rows
- Changing the category taxonomy itself
- Applying item-level hard-skip as the primary path for free-text single expenses
- Automatic decay/expiry of memory rows
- Global (cross-tenant) item or merchant memory sharing

## Dependencies

- **013** — tenant category memory, weight model, reply-edit learning signals
- **014** — receipt-level store name propagated to line items
- **004** — per-line expense persistence
- **005 / 008** — reply-edit and bulk category change
- **017** — confirmation display of multi-category subtotals
