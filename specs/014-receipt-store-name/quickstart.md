# Quickstart: Receipt Store Name Extraction

**Feature**: 014-receipt-store-name

## Prerequisites

- Features **004**, **013** deployed (expenses + category memory)
- Migration `20260629120000_expense_metadata.sql` applied
- `GEMINI_API_KEY` for vision receipt parse
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` for persistence
- Sample receipt image (multi-line supermarket preferred)

## Apply migration

```bash
supabase db push
# Or apply manually:
# supabase/migrations/20260629120000_expense_metadata.sql
```

Verify:

```sql
\d expenses   -- metadata jsonb column
```

## Unit tests

```bash
pytest tests/test_receipt_store_name.py tests/test_merchant_resolve.py \
  tests/test_ai_assist.py tests/test_categorize_memory.py -q
```

## Manual test flow

### 1. Multi-line receipt — store_name on all lines

```bash
python local_run.py --image path/to/aeon_receipt.jpg
```

Expected:
- Multiple line items in confirmation (product descriptions)
- Usage logs: vision parse; **no** `merchant_extract` per line when store normalizes
- DB rows share metadata store:

```sql
SELECT description, metadata->>'store_name' AS store_name, category_source
FROM expenses
ORDER BY created_at DESC
LIMIT 10;
```

All lines from one submission should show the same `store_name` (e.g. `イオン`).

### 2. Merchant memory uses store, not product

After first receipt log, check memory:

```sql
SELECT merchant_key, display_merchant, category_code, weight
FROM category_merchant_memory
ORDER BY updated_at DESC
LIMIT 5;
```

Expect `merchant_key` like `aeon` (not product-derived keys).

### 3. Repeat receipt — memory skip

Log another image or text at same chain (if memory weight ≥ 1.0 from prior correction):

```bash
python local_run.py --image path/to/another_aeon_receipt.jpg
```

- `category_source = 'memory'` when weight threshold met
- No `categorize` scope in usage logs on memory hit

### 4. Text expense — unchanged (no store_name)

```bash
python local_run.py --text "スターバックス ラテ 580円"
```

- `metadata = '{}'` or no store_name key
- `merchant_extract` LLM invoked (013 path)

### 5. Reply-edit uses persisted store_name

1. Log multi-line receipt image
2. Note `bot_message_id`
3. Reply-edit category on one line:

```bash
python local_run.py --reply-to <bot_message_id> --text "食料品"
```

Verify memory upsert used store key (not product description):

```sql
SELECT merchant_key, last_source, weight
FROM category_merchant_memory
WHERE merchant_key = '<expected_chain_key>';
```

### 6. Backfill prefers metadata (post-deploy receipts)

After logging vision receipts with metadata:

```bash
python scripts/backfill_category_memory.py --dry-run
python scripts/backfill_category_memory.py
```

Confirm backfill groups by chain key from `metadata.store_name`, not product lines.

## SC-001 / SC-002 spot check

**SC-001** (≥70% lines share store merchant_key):

```sql
-- After logging several multi-line vision receipts at known chains,
-- compare merchant_key derived from metadata.store_name vs from description heuristic
```

**SC-002** (≥30% relative memory hit rate improvement):

```sql
SELECT category_source, COUNT(*)
FROM expenses
WHERE metadata ? 'store_name'
  AND metadata->>'store_name' IS NOT NULL
GROUP BY category_source;
```

Compare `memory` share before/after 014 on vision receipt cohort.

## Troubleshooting

| Symptom | Check |
| ------- | ----- |
| store_name always null | Vision prompt/schema; receipt header legibility in image |
| Still calls merchant_extract | normalize_merchant_key returned null; check alias YAML |
| Lines have different store_name | propagate_receipt_store_name not wired; inconsistent LLM → null all |
| metadata empty in DB | build_insert_row not passing metadata; migration not applied |
| Backfill ignores store | Script selects metadata column; redeploy 014 backfill changes |

## Related

- Category memory: `specs/013-tenant-category-memory/quickstart.md`
- OCR store heuristics (v2): `specs/014-receipt-store-name/spec.md` User Story 2
