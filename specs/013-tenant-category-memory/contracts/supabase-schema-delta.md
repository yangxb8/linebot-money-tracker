# Supabase Schema Delta: Tenant Category Memory

**Feature**: 013-tenant-category-memory  
**Migration**: `supabase/migrations/20260628120000_category_merchant_memory.sql`

## New table: category_merchant_memory

```sql
CREATE TABLE category_merchant_memory (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_type text NOT NULL CHECK (tenant_type IN ('user', 'group', 'room')),
    tenant_id text NOT NULL,
    merchant_key text NOT NULL,
    display_merchant text,
    category_code text NOT NULL,
    weight numeric(6, 2) NOT NULL DEFAULT 0 CHECK (weight >= 0),
    hit_count int NOT NULL DEFAULT 0,
    last_source text NOT NULL CHECK (
        last_source IN ('llm', 'user_correction', 'silent_confirm', 'backfill')
    ),
    last_corrected_by text,
    sample_description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_type, tenant_id, merchant_key)
);

CREATE INDEX idx_category_merchant_memory_lookup
    ON category_merchant_memory (tenant_type, tenant_id, merchant_key);
```

No RLS in v1 (service role bot writes only).

## Alter table: expenses

```sql
ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS category_guess_code text,
    ADD COLUMN IF NOT EXISTS category_source text
        CHECK (category_source IS NULL OR category_source IN ('memory', 'llm'));
```

## RPC: get_category_accuracy_stats

```sql
CREATE OR REPLACE FUNCTION get_category_accuracy_stats(
    p_tenant_type text,
    p_tenant_id text,
    p_days int DEFAULT 30
)
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
  -- Implementation: count expenses in window;
  -- pct_guess_unknown = unknown guess / total;
  -- pct_guess_unchanged = guess matched final category without category audit
$$;
```

Grant execute to `service_role` only for v1.

## Backfill

Invoked from Python `scripts/backfill_category_memory.py` after migration (not inline LLM in SQL):

```bash
python scripts/backfill_category_memory.py [--dry-run]
```

Reads all expenses, applies YAML/heuristic merchant keys, upserts memory idempotently.

## Rollback notes

- Drop `category_merchant_memory`
- Drop `expenses.category_guess_code`, `expenses.category_source`
- Drop `get_category_accuracy_stats`
