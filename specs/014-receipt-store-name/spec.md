# Feature Specification: Receipt Store Name Extraction

**Feature Branch**: `014-receipt-store-name`

**Created**: 2026-06-24

**Status**: Draft (deferred — not in 013 scope)

**Input**: Receipt parser and LLM vision pipeline should expose a `store_name` field distinct from line-item descriptions, so category memory (013) can key on the store for multi-line grocery receipts instead of each product line.

## Problem

Multi-line receipts (supermarket, drugstore) produce descriptions like `牛乳`, `食パン`, `卵` per line. Feature 013 merchant memory keys on **merchant name only**. Without `store_name`, each line gets a weak or missing merchant key and cannot benefit from store-level memory (e.g. all `イオン` receipt lines → `food.grocery`).

## User Scenarios & Testing

### User Story 1 — Grocery receipt uses store for all lines (Priority: P1)

A user photographs an Aeon receipt with 8 line items. Every persisted expense line stores `store_name: イオン` (or normalized equivalent) while `description` remains the product name.

**Acceptance Scenarios**:

1. **Given** OCR or LLM vision parse of a multi-line receipt with header store name, **When** items are extracted, **Then** each item includes optional `store_name` populated from header/register merchant field.
2. **Given** `store_name` present, **When** 013 merchant extraction runs, **Then** it prefers `store_name` over line `description` for `merchant_key`.
3. **Given** single-line text expense (no receipt), **When** logged, **Then** `store_name` is null and 013 uses description-only LLM extraction (unchanged).

---

### User Story 2 — OCR register receipts (Priority: P2)

Legacy OCR `receipt_parser` path extracts store from top lines when pattern matches (e.g. first non-empty line before item block).

**Acceptance Scenarios**:

1. **Given** OCR text with store on line 1 and items below, **When** `parse_text_for_expenses` runs, **Then** all items share the same `store_name`.
2. **Given** OCR cannot detect store, **When** items are returned, **Then** `store_name` is null (fallback to per-line merchant LLM).

## Requirements (draft)

- **FR-001**: Expense item dict MUST support optional `store_name: string | null` from parse through persist.
- **FR-002**: LLM vision receipt prompt MUST request `store_name` at receipt level applied to all line items.
- **FR-003**: OCR parser SHOULD heuristically set `store_name` from receipt header when confidence is high.
- **FR-004**: `store_name` is NOT persisted as a separate DB column in v1 of 014 (passed in memory pipeline only) unless analytics require it later.
- **FR-005**: 013 `merchant_extract` MUST prefer `store_name` over `description` when non-empty.

## Out of Scope

- Store geolocation or branch-level keys
- Separate store master table
- Web UI for store names

## Dependencies

- **013** — tenant category memory consumes `store_name`
- **004** — expense item shape in message handler

## Success Criteria (draft)

- **SC-001**: For multi-line receipt logs at known chains, **≥70%** of lines share the same `merchant_key` as the store header (not product name).
- **SC-002**: Category memory hit rate for supermarket receipts improves **≥30% relative** vs 013 without `store_name`.

## Assumptions

- Store name on Japanese receipts usually appears in first 1–3 lines or above item table.
- Same implementation can be phased: LLM vision first, OCR heuristics second.
