# Supabase Schema Delta: Expense Metadata (store_name)

**Feature**: 014-receipt-store-name  
**Migration**: `supabase/migrations/20260629120000_expense_metadata.sql`

## Alter table: expenses

```sql
ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}';
```

**Notes**:
- No dedicated `store_name` column (FR-004)
- Application writes `{"store_name": "<raw>"}` when vision parse provides value
- Empty object `{}` when absent

## Example rows

```sql
-- Vision receipt line with store
INSERT INTO expenses (..., description, metadata)
VALUES (..., '牛乳', '{"store_name": "イオン"}');

-- Text expense (unchanged)
INSERT INTO expenses (..., description, metadata)
VALUES (..., 'スターバックス ラテ', '{}');
```

## Application changes

`ExpenseInsertRow` gains:

| Field | Type | Source |
| ----- | ---- | ------ |
| metadata | dict | `{"store_name": item["store_name"]}` if non-empty else `{}` |

`build_insert_row` populates from item dict after vision propagate.

## Read paths (014)

| Consumer | Select | Usage |
| -------- | ------ | ----- |
| backfill_category_memory.py | `metadata, description, ...` | Prefer metadata.store_name |
| reply_edit correction | expense by id | Pass store_name to memory helper |
| Web dashboard | not in v1 scope | — |

## Rollback notes

```sql
ALTER TABLE expenses DROP COLUMN IF EXISTS metadata;
```

Existing 013 columns (`category_guess_code`, `category_source`) unaffected.

## RLS

No change — bot service role writes; same as 004/013.
