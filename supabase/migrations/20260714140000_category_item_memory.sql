-- Item-level category memory (feature 018)
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

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

DO $$
DECLARE
    con_name text;
BEGIN
    SELECT c.conname INTO con_name
    FROM pg_constraint c
    JOIN pg_class t ON c.conrelid = t.oid
    WHERE t.relname = 'expenses'
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) ILIKE '%category_source%';
    IF con_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE expenses DROP CONSTRAINT %I', con_name);
    END IF;
END $$;

ALTER TABLE expenses ADD CONSTRAINT expenses_category_source_check
    CHECK (
        category_source IS NULL
        OR category_source IN ('memory', 'item_memory', 'llm')
    );

GRANT SELECT, INSERT, UPDATE, DELETE ON category_item_memory TO service_role;
