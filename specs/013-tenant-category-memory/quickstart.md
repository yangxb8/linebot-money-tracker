# Quickstart: Tenant Category Memory

**Feature**: 013-tenant-category-memory

## Prerequisites

- Features **004–006**, **010** complete (expenses, reply-edit, tenant scope, taxonomy)
- `GEMINI_API_KEY` for merchant extract + categorize
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` for memory persistence
- Python deps installed (`pip install -r requirements.txt`)

## Apply migration

```bash
# From repo root
supabase db push
# Or apply manually:
# supabase/migrations/20260628120000_category_merchant_memory.sql
```

Verify:

```sql
\d category_merchant_memory
\d expenses   -- category_guess_code, category_source columns
SELECT proname FROM pg_proc WHERE proname = 'get_category_accuracy_stats';
```

## Run backfill (one-time)

```bash
python scripts/backfill_category_memory.py --dry-run
python scripts/backfill_category_memory.py
```

Confirm rows:

```sql
SELECT tenant_type, tenant_id, merchant_key, category_code, weight, last_source
FROM category_merchant_memory
ORDER BY updated_at DESC
LIMIT 20;
```

## Manual test flow

### 1. First log — LLM path

```bash
python local_run.py --text "スターバックス ラテ 580円"
```

- Confirmation shows `カテゴリ（推測）` (unchanged label).
- Usage logs show `merchant_extract` + `categorize` scopes.
- DB: `expenses.category_source = 'llm'`.

```sql
SELECT category_guess_code, category_source FROM expenses
ORDER BY created_at DESC LIMIT 1;
```

### 2. Teach memory via correction

Note `bot_message_id` from output, then:

```bash
python local_run.py --reply-to <bot_message_id> --text "外食"
```

Pick category option if prompted (1/2/3). Verify memory:

```sql
SELECT merchant_key, category_code, weight, last_source
FROM category_merchant_memory
WHERE display_merchant ILIKE '%スタバ%' OR merchant_key = 'starbucks';
```

Expect `weight = 1.0`, `last_source = user_correction'`.

### 3. Repeat merchant — memory skip

```bash
python local_run.py --text "スターバックス 渋谷店 680円"
```

- Same category as correction without reply-edit.
- Usage logs: `merchant_extract` only — **no** `categorize` scope.
- `expenses.category_source = 'memory'`.

### 4. Silent confirm path

1. Log a new merchant (no prior memory): `ローソン おにぎり 150円`
2. Do **not** reply-edit.
3. Log again: `ローソン コーヒー 120円`

Check weight progression:

```sql
SELECT merchant_key, weight, hit_count, last_source
FROM category_merchant_memory
WHERE merchant_key = 'lawson';
```

After two logs without correction: weight should be `0.25 + 0.5 = 0.75` (first log seeds, second applies silent confirm on prior).

### 5. Generic description — always LLM

```bash
python local_run.py --text "食費 5000円"
python local_run.py --text "食費 3000円"
```

Both should invoke `categorize` scope. No memory row for generic key:

```sql
SELECT * FROM category_merchant_memory WHERE merchant_key IN ('食費', 'shokuhi');
-- expect 0 rows
```

### 6. Group shared memory

```bash
python local_run.py --group-id <group_id> --text "ドンキ 雑貨 800円"
# reply-edit to correct category
python local_run.py --group-id <group_id> --text "ドンキホーテ 500円"
```

Second log should use group tenant memory (same `tenant_id` = group_id).

### 7. Analytics RPC

```sql
SELECT get_category_accuracy_stats('user', '<LINE_USER_ID>', 30);
```

Expect JSON with `pct_guess_unchanged` and `pct_guess_unknown`.

## Unit tests

```bash
pytest tests/test_merchant_normalize.py tests/test_merchant_extract.py \
  tests/test_category_memory.py tests/test_categorize_memory.py -q
```

## Troubleshooting

| Symptom | Check |
| ------- | ----- |
| Always calls categorize | Memory `weight < 1.0`; merchant extract returned null; alias mismatch |
| Wrong category from memory | `category_merchant_memory.category_code` for tenant; run correction to overwrite |
| Backfill empty | Expenses lack extractable merchant in description; run without `--dry-run` |
| Group member doesn't see memory | `tenant_type`/`tenant_id` on memory row matches group, not personal |
| Merchant extract errors | `GEMINI_API_KEY`; falls back to categorize-only (no memory write) |

## Related

- Receipt `store_name`: `specs/014-receipt-store-name/spec.md` (not required for 013 MVP)
- Merchant alias list: `specs/013-tenant-category-memory/appendix-merchant-alias-seed.md`
