# Research: Receipt Store Name Extraction

**Feature**: 014-receipt-store-name

## Decision 1: Vision-only v1 scope

**Decision**: Ship store_name extraction only on the LLM vision path (`assist_parse_image` → `process_image_message`). Defer OCR `receipt_parser` header heuristics to 014 v2.

**Rationale**: Clarified in spec session 2026-06-26. Production image pipeline already uses Gemini vision exclusively; OCR path is legacy/unused in production.

**Alternatives considered**:
- **Both vision + OCR in v1** — rejected; increases scope and test surface without blocking 013 value.
- **OCR first** — rejected; production uses vision.

## Decision 2: Receipt-level store_name in LLM JSON

**Decision**: Extend the vision parse response object with a top-level optional field:

```json
{
  "store_name": "イオン",
  "items": [...],
  "total": 1280,
  "currency": "JPY"
}
```

`store_name` is `string | null`. Prompt instructs: merchant/store from receipt header or register banner, not product line text.

**Rationale**: Matches FR-002; single field avoids per-line inconsistency in model output; simpler schema validation.

**Alternatives considered**:
- **Per-item store_name in LLM output** — rejected; redundant and error-prone; unified in post-process anyway.

## Decision 3: Post-process unify (`propagate_receipt_store_name`)

**Decision**: After schema validation, copy receipt-level `store_name` onto every item dict as `item['store_name']`. Rules:

1. Strip whitespace; empty string → treat as null
2. If any item already has a conflicting non-null `store_name` differing from receipt-level → set null on **all** lines
3. If receipt-level null/absent → all items get `store_name: null` (omit key or explicit null)

**Rationale**: Spec clarification — consistent merchant_key across receipt lines; safe fallback when model inconsistent.

## Decision 4: Merchant LLM skip when store_name present

**Decision**: New `resolve_raw_merchant(item, gemini)`:

1. Read `item.get('store_name')`; if non-empty, apply `strip_branch_suffix` + `normalize_merchant_key`
2. If key non-null → return `(raw_merchant, merchant_key)` **without** calling `extract_merchant_name`
3. Else → await `extract_merchant_name(description, ...)` (013 path)

**Rationale**: Spec clarification; reduces LLM cost/latency for receipt flows; fallback preserves behavior for unknown chains.

## Decision 5: Persist in `expenses.metadata` jsonb

**Decision**: Add `metadata jsonb NOT NULL DEFAULT '{}'` to `expenses`. When `store_name` present at insert:

```json
{"store_name": "イオン"}
```

No top-level `store_name` column.

**Rationale**: Spec clarification (option B). Supports 013 backfill and reply-edit re-derivation without schema churn for future metadata keys.

**Alternatives considered**:
- **Ephemeral only** — rejected by user; loses audit/backfill value.
- **Dedicated column** — rejected in spec FR-004.

## Decision 6: Raw storage vs normalized storage

**Decision**: Persist LLM-extracted raw `store_name` in metadata. Apply `normalize_merchant_key` only when deriving `merchant_key` for memory.

**Rationale**: FR-004; preserves display/audit fidelity; normalization rules can evolve without rewriting stored values.

## Decision 7: Reply-edit and backfill prefer metadata

**Decision**:

- **Backfill**: `merchant_key_from_expense_row(row)` checks `row.metadata.get('store_name')` first, then heuristic on description.
- **Reply-edit**: When recording category correction, load expense row metadata; pass `store_name` to `record_user_correction_from_description` / `record_user_correction`.

**Rationale**: FR-006; aligns with user expectation that persisted store supports future memory learning.

## Decision 8: Text and OCR paths unchanged

**Decision**: `assist_parse_text`, `assist_parse_ocr`, and `parse_text_for_expenses` do not set `store_name` in v1. Items lack key → 013 description-only merchant path.

**Rationale**: v1 scope; avoids partial OCR behavior before v2 heuristics.

## Decision 9: Success criteria measurement

**Decision**: SC-001/SC-002 evaluated on LLM vision receipt submissions only (014 v1).

**Measurement approach**:
- **SC-001**: Sample multi-line vision logs at known chains; count lines where `merchant_key` matches normalized header store (not product-derived key).
- **SC-002**: Compare memory hit rate (`category_source = 'memory'`) for vision supermarket receipts before/after 014 deploy.

## Decision 10: Module placement

**Decision**:
- `services/receipt_store_name.py` — unify/propagate helpers (pure functions, easy to test)
- `services/merchant_resolve.py` — async merchant resolution shared by categorize, reply-edit, backfill helpers

**Rationale**: Keeps `ai_assist.py` focused on LLM I/O; keeps `categorize.py` orchestration thin.

## Decision 11: 014 v2 boundary (OCR)

**Decision**: Document only in spec/plan; no code stubs in v1. v2 will add header heuristic in `receipt_parser` and set `store_name` before same propagate/resolve pipeline.

**Rationale**: Spec explicitly defers User Story 2 / FR-003.
