# Feature Specification: Receipt Store Name Extraction

**Feature Branch**: `014-receipt-store-name`

**Created**: 2026-06-24

**Status**: Implemented (014 v1)

**Input**: Receipt parser and LLM vision pipeline should expose a `store_name` field distinct from line-item descriptions, so category memory (013) can key on the store for multi-line grocery receipts instead of each product line.

## Clarifications

### Session 2026-06-26

- Q: 014 v1 scope (LLM vision vs OCR heuristics)? → A: **LLM vision only** — OCR header heuristics (User Story 2 / FR-003) deferred to 014 v2.
- Q: Merchant LLM when `store_name` present? → A: **Skip merchant LLM** — use `store_name` as `raw_merchant`, run `normalize_merchant_key`; fall back to description LLM only if normalization returns null.
- Q: Persist `store_name` on expense rows? → A: **Yes, in expense JSON metadata** — no dedicated DB column; each persisted line includes optional `store_name` in expense metadata for backfill, reply-edits, and audit.
- Q: Per-line vs receipt-level `store_name`? → A: **Receipt-level unify** — one value per receipt parse propagated to all lines; if absent or inconsistent across lines, set `store_name: null` on all lines.
- Q: Success criteria measurement scope (014 v1)? → A: **LLM vision receipts only** — SC-001/SC-002 apply to photo/vision receipt flows in v1.

## Problem

Multi-line receipts (supermarket, drugstore) produce descriptions like `牛乳`, `食パン`, `卵` per line. Feature 013 merchant memory keys on **merchant name only**. Without `store_name`, each line gets a weak or missing merchant key and cannot benefit from store-level memory (e.g. all `イオン` receipt lines → `food.grocery`).

## User Scenarios & Testing

### User Story 1 — Grocery receipt uses store for all lines (Priority: P1)

A user photographs an Aeon receipt with 8 line items. Every persisted expense line includes optional `store_name: イオン` in expense metadata while `description` remains the product name.

**Acceptance Scenarios**:

1. **Given** LLM vision parse of a multi-line receipt with header store name, **When** items are extracted, **Then** post-processing assigns one receipt-level `store_name` to every line item (or `null` on all lines if missing/inconsistent).
2. **Given** non-empty `store_name`, **When** 013 merchant extraction runs, **Then** it skips the merchant LLM, normalizes `store_name` for `merchant_key`, and falls back to description LLM only when normalization returns null.
3. **Given** single-line text expense (no receipt), **When** logged, **Then** `store_name` is null and 013 uses description-only LLM extraction (unchanged).

---

### User Story 2 — OCR register receipts (Priority: P2, deferred to 014 v2)

Legacy OCR `receipt_parser` path extracts store from top lines when pattern matches (e.g. first non-empty line before item block). **Not in 014 v1 scope.**

**Acceptance Scenarios** (014 v2):

1. **Given** OCR text with store on line 1 and items below, **When** `parse_text_for_expenses` runs, **Then** all items share the same `store_name`.
2. **Given** OCR cannot detect store, **When** items are returned, **Then** `store_name` is null (fallback to per-line merchant LLM).

## Requirements (draft)

- **FR-001**: Expense item dict MUST support optional `store_name: string | null` from parse through categorization and persistence.
- **FR-002**: LLM vision receipt prompt MUST request a single receipt-level `store_name` (not per-line variants). Post-processing MUST propagate that value to all extracted line items, or set `store_name: null` on all lines when absent or inconsistent.
- **FR-003** *(014 v2)*: OCR parser SHOULD heuristically set `store_name` from receipt header when confidence is high.
- **FR-004**: `store_name` MUST NOT be a dedicated top-level DB column in 014 v1. It MUST be persisted on each expense row inside JSON metadata (e.g. `metadata.store_name`) when present. Normalization applies only when deriving `merchant_key`, not when storing the raw value.
- **FR-005**: When `store_name` is non-empty, categorization MUST skip `merchant_extract` LLM, use `store_name` as `raw_merchant`, and derive `merchant_key` via `normalize_merchant_key`. If normalization returns null, fall back to description-based `merchant_extract` LLM (unchanged 013 path).
- **FR-006**: 013 backfill and reply-edit merchant derivation MUST prefer persisted `metadata.store_name` over line `description` when non-empty (same skip-LLM / normalize / fallback rules as FR-005).

## Out of Scope (014 v1)

- OCR header heuristics in `receipt_parser` (User Story 2 / FR-003 — planned for 014 v2)
- Store geolocation or branch-level keys
- Separate store master table
- Web UI for store names

## Dependencies

- **013** — tenant category memory consumes `store_name` at log time to derive `merchant_key`; live memory lookup uses `category_merchant_memory`, not expense rows. Persisted `metadata.store_name` supports 013 backfill and reply-edit merchant re-derivation.
- **004** — expense item shape in message handler

## Success Criteria (draft)

- **SC-001**: For multi-line **LLM vision** receipt logs at known chains (014 v1 scope), **≥70%** of lines share the same `merchant_key` as the store header (not product name).
- **SC-002**: Category memory hit rate for **LLM vision** supermarket receipts improves **≥30% relative** vs 013 without `store_name`.

## Assumptions

- Store name on Japanese receipts usually appears in first 1–3 lines or above item table.
- **014 v1** ships LLM vision only; OCR header heuristics follow in **014 v2**.
