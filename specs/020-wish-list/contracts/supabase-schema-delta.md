# Supabase Schema Delta: Wish List

**Feature**: 020-wish-list  
**Target project**: `https://nyuenufldaqsjybjhawl.supabase.co`

## Migration (new file)

`supabase/migrations/YYYYMMDDHHMMSS_wish_list_items.sql`

## DDL sketch

```sql
CREATE TABLE wish_list_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_type text NOT NULL CHECK (tenant_type IN ('user', 'group', 'room')),
    tenant_id text NOT NULL,
    name text NOT NULL CHECK (char_length(trim(name)) > 0),
    amount numeric(14, 2) NOT NULL CHECK (amount > 0),
    currency char(3) NOT NULL DEFAULT 'JPY',
    assigned_level smallint NOT NULL CHECK (assigned_level IN (1, 2, 3)),
    category_node_id uuid NOT NULL REFERENCES category_nodes(id),
    category_l1_id uuid NOT NULL REFERENCES category_nodes(id),
    category_l2_id uuid REFERENCES category_nodes(id),
    category_l3_id uuid REFERENCES category_nodes(id),
    product_url text,
    sort_order int NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'executed')),
    executed_expense_id uuid REFERENCES expenses(id) ON DELETE SET NULL,
    created_by_line_user_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    CONSTRAINT wish_list_executed_chk CHECK (
        (status = 'active' AND executed_expense_id IS NULL)
        OR (status = 'executed' AND executed_expense_id IS NOT NULL)
        OR (deleted_at IS NOT NULL)
    )
);

CREATE INDEX wish_list_items_active_order_idx
    ON wish_list_items (tenant_type, tenant_id, sort_order)
    WHERE status = 'active' AND deleted_at IS NULL;

CREATE INDEX wish_list_items_tenant_status_idx
    ON wish_list_items (tenant_type, tenant_id, status)
    WHERE deleted_at IS NULL;

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS wish_list_item_id uuid
        REFERENCES wish_list_items(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS expenses_wish_list_item_id_idx
    ON expenses (wish_list_item_id)
    WHERE wish_list_item_id IS NOT NULL AND deleted_at IS NULL;
```

> Note: Circular FK (`wish_list_items.executed_expense_id` ↔ `expenses.wish_list_item_id`) may require creating one column nullable without FK first, or deferring one FK. Prefer: create `wish_list_items` without `executed_expense_id` FK initially, add `expenses.wish_list_item_id`, then add `executed_expense_id` FK — or use `ON DELETE SET NULL` and add constraints in a second statement after both tables/columns exist.

## RLS / grants

Follow periodic_expense_schedules / expenses patterns used by the web admin client (service role for bot; authenticated policies or server-route service role with `assertTenantAccess` as currently practiced for budget/periodic). Document the chosen approach in the migration comments to match repo convention at implement time.

## View delta (optional)

If `v_expenses_enriched` is a hard column list, refresh/recreate it to pass through `wish_list_item_id`. If it is `e.*`, no change required.
