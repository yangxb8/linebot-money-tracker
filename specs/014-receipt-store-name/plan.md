# Implementation Plan: Receipt Store Name Extraction

**Branch**: `014-receipt-store-name` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)

**Input**: LLM vision receipt parsing exposes receipt-level `store_name`, propagated to all line items and persisted in expense `metadata` JSON. Feature 013 uses `store_name` to derive `merchant_key` without a merchant LLM call when normalization succeeds. OCR header heuristics deferred to 014 v2.

## Summary

Extend the **Gemini vision receipt pipeline** (`assist_parse_image`) to return a receipt-level `store_name`, post-process to unify across line items, and thread `store_name` through categorization and Supabase persistence. Add **`expenses.metadata` jsonb** (no dedicated column) with `metadata.store_name`. Update **`classify_expense_with_memory`** to skip `merchant_extract` LLM when `store_name` normalizes; fall back to description LLM on normalize failure. Update **013 backfill** and **reply-edit** paths to prefer persisted `metadata.store_name`.

## Technical Context

**Language/Version**: Python 3.11+ (LINE bot); SQL (Supabase Postgres migrations)

**Primary Dependencies**: Existing `assist_parse_image`, `classify_expense_with_memory`, `normalize_merchant_key`, `expense_repository`, `category_memory`, `reply_edit`

**Storage**: Supabase Postgres — `expenses.metadata jsonb` with optional `store_name` key

**Testing**: pytest for vision schema validation, store_name unify post-process, merchant skip/fallback, metadata persistence, backfill/reply-edit preference; manual quickstart with `--image`

**Target Platform**: LINE bot (Cloud Run) + Supabase hosted Postgres

**Performance Goals**: Skip one LLM call (`merchant_extract`) per receipt line when `store_name` normalizes; no added latency beyond existing vision parse

**Constraints**:
- 014 v1 = LLM vision only (no OCR `receipt_parser` heuristics)
- Receipt-level unify: one `store_name` per parse or null on all lines
- Raw `store_name` stored; normalization only for `merchant_key`
- No dedicated `store_name` column; JSON metadata only
- Confirmation UX unchanged (013 labels)
- Depends on 013 merchant memory being deployed

**Scale/Scope**: Multi-line grocery/drugstore receipts (typically 3–20 lines); metadata adds ~50 bytes per row when present

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Centralize merchant resolution in one helper; extend existing vision schema rather than new pipeline |
| Test-First Delivery | pytest for parse unify, categorize skip/fallback, metadata round-trip, backfill preference |
| User Experience Consistency | No confirmation copy changes; same bot reply structure |
| Performance & Reliability | Fewer LLM calls on receipt logs; graceful fallback to description merchant LLM |
| Observability & Feedback | Log when store_name used vs fallback; metadata visible in DB for audit |

**Gate**: PASS

**Post-design re-check**: PASS — extends 013 categorize path and 004 expense insert; no breaking API for text/OCR-only flows.

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  LINE image message → preprocess_receipt_image                  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  assist_parse_image (Gemini vision)                             │
│    JSON: { store_name, items[], total, currency }               │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  propagate_receipt_store_name(items, store_name)                │
│    → each item dict gets store_name (or null all if inconsistent)│
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  classify_expense_with_memory(item)                             │
│    resolve_raw_merchant(item):                                  │
│      store_name? → normalize_merchant_key (skip merchant LLM)   │
│      else / normalize null → extract_merchant_name(description) │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  build_insert_row → expenses.metadata = {"store_name": "..."}   │
│  category_merchant_memory upsert (013, unchanged weight model)  │
└─────────────────────────────────────────────────────────────────┘
```

### Merchant resolution (014 delta on 013 flow)

1. If `item.get('store_name')` non-empty after strip:
   - `raw_merchant = strip_branch_suffix(store_name)` (same hygiene as merchant_extract)
   - `merchant_key = normalize_merchant_key(raw_merchant)`
   - If `merchant_key`: skip `extract_merchant_name` LLM
2. If no store_name or normalize returns null: existing 013 path (`extract_merchant_name` on description)
3. Memory lookup / category LLM unchanged from 013

### Persistence

| Field | Location | Notes |
| ----- | -------- | ----- |
| `store_name` (raw) | `expenses.metadata->>'store_name'` | Set when vision parse provides value |
| `merchant_key` | `category_merchant_memory` | Derived at log time (013) |
| `description` | `expenses.description` | Product line name unchanged |

## Project Structure

### Documentation

```text
specs/014-receipt-store-name/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── receipt-vision-parse.md
│   ├── merchant-resolution.md
│   └── supabase-schema-delta.md
└── tasks.md             # /speckit-tasks
```

### Source Code

```text
supabase/migrations/
  20260629120000_expense_metadata.sql

services/
  ai_assist.py                    # vision prompt + schema + ReceiptImageParseResult.store_name
  receipt_store_name.py           # NEW — propagate/unify store_name onto item dicts
  merchant_resolve.py             # NEW — resolve_raw_merchant(item, gemini) shared helper
  categorize.py                   # classify_expense_with_memory uses merchant_resolve
  expense_repository.py           # metadata in ExpenseInsertRow / build_insert_row
  category_memory.py              # backfill + reply-edit prefer metadata.store_name
  message_handler.py              # wire propagate after vision parse
  reply_edit.py                   # pass metadata.store_name to correction helper

scripts/
  backfill_category_memory.py     # select metadata; prefer store_name for merchant key

tests/
  test_receipt_store_name.py      # NEW — unify logic
  test_merchant_resolve.py        # NEW — skip LLM / fallback
  test_ai_assist.py               # extend — store_name in vision parse
  test_categorize_memory.py       # extend — store_name path
  test_message_handler.py         # extend — image pipeline carries store_name
  test_expense_repository.py      # NEW or extend — metadata persist
  test_backfill_category_memory.py # extend — metadata preference
```

## Implementation Phases

### Phase 1 — Schema (blocking)

1. Migration: add `metadata jsonb NOT NULL DEFAULT '{}'` to `expenses`.
2. Document contract in `contracts/supabase-schema-delta.md`.

### Phase 2 — Vision parse & post-process

1. Extend `_RECEIPT_IMAGE_PROMPT` with receipt-level `store_name` field and rules (header/register merchant, not product names).
2. Extend `RECEIPT_IMAGE_PARSE_SCHEMA` — optional `store_name: string | null`.
3. Extend `ReceiptImageParseResult` with `store_name`.
4. Implement `propagate_receipt_store_name()` in `receipt_store_name.py`.
5. Call from `_extract_expense_items_from_image` after `_prepare_llm_receipt_items`.
6. pytest: valid parse with store_name; inconsistent per-line override → null all; absent → null.

### Phase 3 — Merchant resolution

1. Implement `resolve_raw_merchant(item, gemini)` in `merchant_resolve.py`.
2. Wire into `classify_expense_with_memory` (replace inline extract call).
3. pytest: store_name skips merchant_extract mock; normalize failure falls back; text item unchanged.

### Phase 4 — Persistence

1. Add `metadata: dict` to `ExpenseInsertRow`; `build_insert_row` sets `{"store_name": ...}` when present.
2. Ensure `insert_expenses` serializes jsonb correctly.
3. pytest: insert row includes metadata when item has store_name.

### Phase 5 — 013 integration (backfill + reply-edit)

1. `backfill_category_memory.py`: select `metadata`; helper `merchant_key_from_expense_row(row)`.
2. `record_user_correction_from_description`: accept optional `store_name`; prefer over description.
3. `reply_edit`: load expense metadata, pass `store_name` on category correction.
4. `find_prior_expense_for_merchant`: prefer metadata store_name when scanning rows (optional improvement).
5. pytest for backfill and reply-edit paths.

### Phase 6 — Verification

1. Full pytest green.
2. Manual quickstart: multi-line receipt image → shared merchant_key across lines.
3. Verify SC-001 sample: log Aeon-like receipt, check memory rows use chain key not product names.

## Risks & Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| LLM omits store_name on clear receipts | Fallback to per-line description LLM (013 behavior); SC-001 tracks ≥70% success |
| Inconsistent LLM store_name across items | Receipt-level unify → null all → safe fallback |
| Metadata not in web dashboard | Out of scope v1; bot-only feature |
| Backfill cannot recover store_name for old rows | Pre-014 expenses lack metadata; heuristic on description only (unchanged) |
| Extra jsonb size | Small string per row; only when vision provides store |

## Dependencies

- **013** — `classify_expense_with_memory`, `category_merchant_memory`, `normalize_merchant_key`
- **004** — expense insert pipeline
- **002** — `assist_parse_image` vision path

## Suggested Next Command

After plan approval: `/speckit-tasks specs 014` to generate `tasks.md`.
