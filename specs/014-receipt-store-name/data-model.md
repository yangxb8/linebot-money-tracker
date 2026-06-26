# Data Model: Receipt Store Name Extraction

**Feature**: 014-receipt-store-name

## ERD (conceptual)

```text
ReceiptImageParseResult
    store_name (optional)
    items[] ──► Expense item dict { description, amount, currency, store_name? }
                      │
                      ▼
              classify_expense_with_memory
                      │
                      ▼
              expenses.metadata.store_name  (persisted raw)
              category_merchant_memory.merchant_key  (derived, 013)
```

## In-memory: expense item dict (parse → categorize → persist)

Extended fields on the dict flowing through `message_handler`:

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| description | string | yes | Product/service line text |
| amount | number | yes | Tax-inclusive line total (vision) |
| currency | string | yes | ISO 4217 |
| store_name | string \| null | no | Receipt-level merchant; same on all lines from one vision parse |
| category_guess_code | string | no | Added during enrich (013) |
| category_source | string | no | `memory` \| `llm` (013) |

**Validation**:
- `store_name`: if present, non-empty after strip; max ~120 chars (truncate in persist if needed)
- Text/OCR items: `store_name` absent or null

## Entity: expenses (delta)

Add column to existing `expenses` table:

| Column | Type | Notes |
| ------ | ---- | ----- |
| metadata | jsonb NOT NULL DEFAULT '{}' | Extensible bag; 014 uses `store_name` key only |

**Metadata shape (014 v1)**:

```json
{
  "store_name": "イオン"
}
```

When no store detected:

```json
{}
```

**Constraints**:
- No CHECK on metadata keys in v1 (app validates)
- Existing rows: `{}` default

**Not stored in metadata**:
- `merchant_key` ( lives in `category_merchant_memory`)
- Normalized store slug

## Entity: ReceiptImageParseResult (application)

Dataclass returned by `validate_receipt_image_parse`:

| Field | Type | Notes |
| ----- | ---- | ----- |
| items | list[dict] | Validated line items (no store_name yet) |
| total | Decimal | Receipt cash total |
| currency | string | Receipt currency |
| store_name | str \| None | NEW — raw receipt-level merchant |

Post-process copies `store_name` onto each item via `propagate_receipt_store_name`.

## Relationship to category_merchant_memory (013)

| Step | Input | Output |
| ---- | ----- | ------ |
| Log time | `item.store_name` or description | `merchant_key` via normalize or LLM |
| Memory upsert | `merchant_key`, category | `category_merchant_memory` row |
| Later logs | `merchant_key` lookup | Skip category LLM when weight ≥ 1.0 |
| Backfill | `metadata.store_name` or description heuristic | Rebuild memory rows |

Live memory lookup does **not** read `expenses.metadata` — only derived `merchant_key` at log/backfill time.

## Functions

### propagate_receipt_store_name(items, store_name) → list[dict]

Pure function. Returns new item dicts with unified `store_name` field.

### merchant_key_from_expense_row(row) → str | None

Used by backfill. Prefers `row['metadata']['store_name']` when non-empty; else `heuristic_merchant_from_description(description)`.

### resolve_raw_merchant(item, gemini) → tuple[str | None, str | None]

Returns `(raw_merchant, merchant_key)`. Implements FR-005 skip/fallback rules.

## Migration

File: `supabase/migrations/20260629120000_expense_metadata.sql`

```sql
ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}';
```

Optional index deferred (no query-by-store_name in v1).

## 014 v2 (deferred)

OCR path will populate `store_name` on item dicts before the same persistence and merchant resolution pipeline. No schema change expected.
