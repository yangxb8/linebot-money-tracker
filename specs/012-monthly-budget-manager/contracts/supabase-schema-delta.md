# Supabase Schema Delta: Monthly Budget Manager

**Feature**: 012-monthly-budget-manager  
**Migration file**: `supabase/migrations/20260624120000_monthly_budgets_tenant.sql`

## monthly_budgets alterations

### Add columns

```sql
ALTER TABLE monthly_budgets
    ADD COLUMN IF NOT EXISTS tenant_type text,
    ADD COLUMN IF NOT EXISTS tenant_id text,
    ADD COLUMN IF NOT EXISTS budget_level text,
    ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
```

### Backfill from legacy

```sql
UPDATE monthly_budgets b
SET
    tenant_type = 'user',
    tenant_id = b.line_user_id,
    budget_level = CASE cn.level WHEN 1 THEN 'l1' WHEN 2 THEN 'l2' END
FROM category_nodes cn
WHERE cn.id = b.category_node_id;
```

### Drop legacy column + constraints

```sql
ALTER TABLE monthly_budgets DROP COLUMN IF EXISTS line_user_id;

-- Drop old unique constraint on (line_user_id, category_node_id, budget_month, currency)
-- Replace with partial uniques per data-model.md
```

### NOT NULL + checks

```sql
ALTER TABLE monthly_budgets
    ALTER COLUMN tenant_type SET NOT NULL,
    ALTER COLUMN tenant_id SET NOT NULL,
    ALTER COLUMN budget_level SET NOT NULL;

ALTER TABLE monthly_budgets
    ADD CONSTRAINT monthly_budgets_level_check
    CHECK (budget_level IN ('total', 'l1', 'l2'));

ALTER TABLE monthly_budgets
    ADD CONSTRAINT monthly_budgets_category_level_check
    CHECK (
        (budget_level = 'total' AND category_node_id IS NULL)
        OR (budget_level IN ('l1', 'l2') AND category_node_id IS NOT NULL)
    );

ALTER TABLE monthly_budgets
    ADD CONSTRAINT monthly_budgets_amount_positive CHECK (amount > 0);
```

### Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_monthly_budgets_tenant_month
    ON monthly_budgets (tenant_type, tenant_id, budget_month);

CREATE UNIQUE INDEX IF NOT EXISTS monthly_budgets_total_uq
    ON monthly_budgets (tenant_type, tenant_id, budget_month, currency)
    WHERE budget_level = 'total';

CREATE UNIQUE INDEX IF NOT EXISTS monthly_budgets_category_uq
    ON monthly_budgets (tenant_type, tenant_id, category_node_id, budget_month, currency)
    WHERE category_node_id IS NOT NULL;
```

## RLS policies

```sql
CREATE POLICY monthly_budgets_select
    ON monthly_budgets FOR SELECT TO authenticated
    USING (can_access_tenant(tenant_type, tenant_id));

CREATE POLICY monthly_budgets_insert
    ON monthly_budgets FOR INSERT TO authenticated
    WITH CHECK (can_access_tenant(tenant_type, tenant_id));

CREATE POLICY monthly_budgets_update
    ON monthly_budgets FOR UPDATE TO authenticated
    USING (can_access_tenant(tenant_type, tenant_id))
    WITH CHECK (can_access_tenant(tenant_type, tenant_id));

CREATE POLICY monthly_budgets_delete
    ON monthly_budgets FOR DELETE TO authenticated
    USING (can_access_tenant(tenant_type, tenant_id));
```

## Functions

### resolve_budget_bucket (SQL helper)

```sql
CREATE OR REPLACE FUNCTION resolve_budget_bucket(
    p_assigned_level smallint,
    p_category_node_id uuid,
    p_category_l1_id uuid,
    p_tenant_type text,
    p_tenant_id text,
    p_budget_month date,
    p_currency char(3)
) RETURNS text  -- 'l2:{uuid}' | 'l1:{uuid}' | 'total' | 'unbudgeted'
```

Implements cascade from research Decision 4.

### get_budget_summary

```sql
CREATE OR REPLACE FUNCTION get_budget_summary(
    p_tenant_type text,
    p_tenant_id text,
    p_budget_month date,
    p_currency char(3) DEFAULT 'JPY'
) RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
```

- Guard: `can_access_tenant`
- Join tenant category tree (via `ensure_tenant_taxonomy` or direct query)
- Aggregate expenses with bucket assignment
- Return shape per `data-model.md`

## No changes to

- `expenses` table structure
- Bot service role write paths
- `monthly_expense_total` / `yearly_expense_total` signatures (reused for suggestions)

## Rollback notes

- Down migration restores `line_user_id` from `tenant_id` where `tenant_type = 'user'`
- Only safe if no group/room budget rows created
