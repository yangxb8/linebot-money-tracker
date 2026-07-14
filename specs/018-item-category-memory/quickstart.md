# Quickstart: Item-Level Category Memory

**Feature**: 018-item-category-memory

## Prerequisites

- Features **013**, **014**, **017** available on branch
- `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- Python deps: `pip install -r requirements.txt` (use `python3`)

## Apply migration

```bash
# After implementing migration from contracts/supabase-schema-delta.md
supabase db push
# or apply SQL manually in Supabase SQL editor
```

Verify:

```sql
\d category_item_memory
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'expenses'::regclass AND contype = 'c';
```

## Run store+item backfill (one-time)

```bash
python3 scripts/backfill_category_item_memory.py --dry-run
python3 scripts/backfill_category_item_memory.py
```

```sql
SELECT memory_kind, merchant_key, item_key, category_code, weight, last_source
FROM category_item_memory
ORDER BY updated_at DESC
LIMIT 20;
-- Expect memory_kind = 'store_item' only from backfill
```

## Manual tests

### 1. Mixed receipt — no prior item memory (soft prior)

Use a home-center style image (planter + toilet paper) or fixture:

```bash
python3 local_run.py --image path/to/shimachu_receipt.jpg
```

Expect:
- Two (or more) distinct category paths in confirmation / subtotals
- `expenses.category_source = 'llm'` for lines without item hits
- Optional soft prior does **not** force both lines to the same merchant category
- `category_item_memory` store_item seeds (`last_source=llm`, low weight)

### 2. Correct one line only

Reply-edit toilet-paper line to 日用品:

```bash
python3 local_run.py --reply-to <bot_message_id> --text "2 日用品"
```

```sql
SELECT memory_kind, merchant_key, item_key, category_code, weight, last_source
FROM category_item_memory
WHERE item_key ILIKE '%パルプ%' OR sample_description ILIKE '%パルプ%';
```

Expect:
- `store_item` + `item_only` rows for that item, `weight=1.0`, `user_correction`
- **No** change of merchant-only `category_merchant_memory` for 島忠 driven by this edit

### 3. Rematch store+item — skip LLM

Log another receipt containing the same normalized toilet-paper item at same store.

Expect: that line `category_source='item_memory'`; usage metering shows no categorize call for that line when weight ≥ 1.0.

### 4. Cross-store item-only

At a different drugstore, receipt line with matching item_key and no store_item row:

Expect: category from `item_only` (correction-sourced), `source=item_memory`.

### 5. Text path regression

```bash
python3 local_run.py --text "スターバックス ラテ 580円"
```

Expect merchant memory path unchanged (`category_source` `memory`/`llm` only — not item rules).

## pytest focus

```bash
python3 -m pytest -q \
  tests/test_item_normalize.py \
  tests/test_category_item_memory.py \
  tests/test_categorize_item_memory.py \
  tests/test_categorize_memory.py \
  tests/test_reply_edit.py
```
