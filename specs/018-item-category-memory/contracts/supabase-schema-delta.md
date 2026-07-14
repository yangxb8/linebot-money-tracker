# Contract: Supabase Schema Delta (018)

**Feature**: 018-item-category-memory  
**Target**: `https://nyuenufldaqsjybjhawl.supabase.co`

## Migration file

`supabase/migrations/YYYYMMDDHHMMSS_category_item_memory.sql`

## DDL (normative)

```sql
CREATE TABLE IF NOT EXISTS category_item_memory (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_type text NOT NULL CHECK (tenant_type IN ('user', 'group', 'room')),
    tenant_id text NOT NULL,
    memory_kind text NOT NULL CHECK (memory_kind IN ('store_item', 'item_only')),
    merchant_key text,
    item_key text NOT NULL,
    display_merchant text,
    sample_description text,
    category_code text NOT NULL,
    weight numeric(6, 2) NOT NULL DEFAULT 0 CHECK (weight >= 0),
    hit_count int NOT NULL DEFAULT 0,
    last_source text NOT NULL CHECK (
        last_source IN ('llm', 'user_correction', 'silent_confirm', 'backfill')
    ),
    last_corrected_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT category_item_memory_kind_merchant_ck CHECK (
        (memory_kind = 'store_item' AND merchant_key IS NOT NULL)
        OR (memory_kind = 'item_only' AND merchant_key IS NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_category_item_memory_store_item
    ON category_item_memory (tenant_type, tenant_id, merchant_key, item_key)
    WHERE memory_kind = 'store_item';

CREATE UNIQUE INDEX IF NOT EXISTS uq_category_item_memory_item_only
    ON category_item_memory (tenant_type, tenant_id, item_key)
    WHERE memory_kind = 'item_only';

CREATE INDEX IF NOT EXISTS idx_category_item_memory_store_lookup
    ON category_item_memory (tenant_type, tenant_id, merchant_key, item_key)
    WHERE memory_kind = 'store_item';

CREATE INDEX IF NOT EXISTS idx_category_item_memory_item_lookup
    ON category_item_memory (tenant_type, tenant_id, item_key)
    WHERE memory_kind = 'item_only';

ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_category_source_check;
ALTER TABLE expenses ADD CONSTRAINT expenses_category_source_check
    CHECK (
        category_source IS NULL
        OR category_source IN ('memory', 'item_memory', 'llm')
    );

GRANT SELECT, INSERT, UPDATE, DELETE ON category_item_memory TO service_role;
```

## Notes

- Do **not** alter `category_merchant_memory`.
- Constraint name for `expenses.category_source` may differ in live DB; migration MUST discover/drop existing check before recreate (use `pg_constraint` lookup if needed).
- RLS: leave disabled in v1 (service role), consistent with merchant memory table. Enabling RLS later requires explicit deny-all for `anon`/`authenticated` plus service_role bypass.
