# Supabase Schema Delta: Tenant Category Editor

**Feature**: 010-tenant-category-editor

## category_nodes — tenant scope

```sql
ALTER TABLE category_nodes
    ADD COLUMN IF NOT EXISTS tenant_type text,
    ADD COLUMN IF NOT EXISTS tenant_id text,
    ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
    ADD CONSTRAINT category_nodes_tenant_pair_chk CHECK (
        (tenant_type IS NULL AND tenant_id IS NULL)
        OR (tenant_type IS NOT NULL AND tenant_id IS NOT NULL)
    );

-- Drop old global unique on code if present
ALTER TABLE category_nodes DROP CONSTRAINT IF EXISTS category_nodes_code_key;

CREATE UNIQUE INDEX category_nodes_template_code_uq
    ON category_nodes (code)
    WHERE tenant_type IS NULL;

CREATE UNIQUE INDEX category_nodes_tenant_code_uq
    ON category_nodes (tenant_type, tenant_id, code)
    WHERE tenant_type IS NOT NULL;

CREATE INDEX category_nodes_tenant_tree_idx
    ON category_nodes (tenant_type, tenant_id, level, sort_order);
```

Existing seed rows remain template (`tenant_type` / `tenant_id` NULL).

## RLS: category_nodes (replace 009 read-all policy)

```sql
DROP POLICY IF EXISTS category_nodes_select_authenticated ON category_nodes;

CREATE POLICY category_nodes_select
    ON category_nodes FOR SELECT TO authenticated
    USING (
        tenant_type IS NULL
        OR (
            tenant_type = 'user'
            AND tenant_id = current_line_user_id()
        )
        OR (
            tenant_type IN ('group', 'room')
            AND EXISTS (
                SELECT 1 FROM tenant_chat_members tcm
                WHERE tcm.tenant_type = category_nodes.tenant_type
                  AND tcm.tenant_id = category_nodes.tenant_id
                  AND tcm.line_user_id = current_line_user_id()
            )
        )
    );

CREATE POLICY category_nodes_insert_tenant
    ON category_nodes FOR INSERT TO authenticated
    WITH CHECK (/* same tenant access as SELECT, tenant_type IS NOT NULL */);

CREATE POLICY category_nodes_update_tenant
    ON category_nodes FOR UPDATE TO authenticated
    USING (/* tenant access */) WITH CHECK (/* tenant access */);

CREATE POLICY category_nodes_delete_tenant
    ON category_nodes FOR DELETE TO authenticated
    USING (/* tenant access; code != 'unknown' enforced in RPC */);
```

Service role (bot) bypasses RLS for taxonomy reads/writes as today.

## RPC: ensure_tenant_taxonomy

```sql
CREATE OR REPLACE FUNCTION ensure_tenant_taxonomy(
    p_tenant_type text,
    p_tenant_id text
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
-- 1. Return early if tenant rows exist
-- 2. Copy template L1 → L2 with new UUIDs, map code → new_id
-- 3. UPDATE expenses SET category_*_id = mapped ids WHERE tenant matches
$$;
```

Callable from authenticated users with tenant access (or only via Next.js service route for stricter control).

## RPC: delete_category_with_transfer

```sql
CREATE OR REPLACE FUNCTION delete_category_with_transfer(
    p_node_id uuid,
    p_transfer_to_id uuid
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
-- Validate same tenant, target != source, not unknown, not last L1
-- Remap expenses to target (L1 or L2 assignment)
-- Delete children if L1, then delete node
-- RETURN { affected_expenses: N }
$$;
```

## Grants

```sql
GRANT EXECUTE ON FUNCTION ensure_tenant_taxonomy(text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION delete_category_with_transfer(uuid, uuid) TO authenticated;
```

## Bot reads

Bot uses service role:

```python
client.table("category_nodes").select("*").eq("tenant_type", t).eq("tenant_id", id).execute()
```

If empty, fall back to template query `tenant_type.is_("null")`.

## Rollback

1. Drop tenant RPCs and policies.
2. Delete rows WHERE `tenant_type IS NOT NULL`.
3. Drop tenant columns and restore global `UNIQUE(code)`.
