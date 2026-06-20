-- Tenant-scoped category taxonomy (feature 010)
-- Per-tenant editable L1-L2 categories; lazy copy from global template.

ALTER TABLE category_nodes
    ADD COLUMN IF NOT EXISTS tenant_type text,
    ADD COLUMN IF NOT EXISTS tenant_id text,
    ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE category_nodes DROP CONSTRAINT IF EXISTS category_nodes_tenant_pair_chk;
ALTER TABLE category_nodes
    ADD CONSTRAINT category_nodes_tenant_pair_chk CHECK (
        (tenant_type IS NULL AND tenant_id IS NULL)
        OR (tenant_type IS NOT NULL AND tenant_id IS NOT NULL)
    );

ALTER TABLE category_nodes DROP CONSTRAINT IF EXISTS category_nodes_code_key;

CREATE UNIQUE INDEX IF NOT EXISTS category_nodes_template_code_uq
    ON category_nodes (code)
    WHERE tenant_type IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS category_nodes_tenant_code_uq
    ON category_nodes (tenant_type, tenant_id, code)
    WHERE tenant_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS category_nodes_tenant_tree_idx
    ON category_nodes (tenant_type, tenant_id, level, sort_order);

CREATE OR REPLACE FUNCTION can_access_tenant(
    p_tenant_type text,
    p_tenant_id text
) RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT CASE
        WHEN p_tenant_type = 'user' THEN p_tenant_id = current_line_user_id()
        WHEN p_tenant_type IN ('group', 'room') THEN EXISTS (
            SELECT 1
            FROM tenant_chat_members tcm
            WHERE tcm.tenant_type = p_tenant_type
              AND tcm.tenant_id = p_tenant_id
              AND tcm.line_user_id = current_line_user_id()
        )
        ELSE false
    END;
$$;

CREATE OR REPLACE FUNCTION ensure_tenant_taxonomy(
    p_tenant_type text,
    p_tenant_id text
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_template_l1 RECORD;
    v_template_l2 RECORD;
    v_new_l1_id uuid;
    v_code_map jsonb := '{}'::jsonb;
    v_old_id uuid;
    v_new_id uuid;
BEGIN
    IF NOT can_access_tenant(p_tenant_type, p_tenant_id) THEN
        RAISE EXCEPTION 'access denied for tenant %:%', p_tenant_type, p_tenant_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM category_nodes
        WHERE tenant_type = p_tenant_type AND tenant_id = p_tenant_id
    ) THEN
        RETURN;
    END IF;

    FOR v_template_l1 IN
        SELECT * FROM category_nodes
        WHERE tenant_type IS NULL AND level = 1
        ORDER BY sort_order, code
    LOOP
        v_new_l1_id := gen_random_uuid();
        v_code_map := v_code_map || jsonb_build_object(v_template_l1.id::text, v_new_l1_id::text);

        INSERT INTO category_nodes (id, code, name_ja, level, parent_id, sort_order, tenant_type, tenant_id)
        VALUES (
            v_new_l1_id,
            v_template_l1.code,
            v_template_l1.name_ja,
            1,
            NULL,
            v_template_l1.sort_order,
            p_tenant_type,
            p_tenant_id
        );
    END LOOP;

    FOR v_template_l2 IN
        SELECT c.* FROM category_nodes c
        WHERE c.tenant_type IS NULL AND c.level = 2
        ORDER BY c.sort_order, c.code
    LOOP
        v_new_id := gen_random_uuid();
        v_code_map := v_code_map || jsonb_build_object(v_template_l2.id::text, v_new_id::text);

        INSERT INTO category_nodes (id, code, name_ja, level, parent_id, sort_order, tenant_type, tenant_id)
        VALUES (
            v_new_id,
            v_template_l2.code,
            v_template_l2.name_ja,
            2,
            (v_code_map ->> v_template_l2.parent_id::text)::uuid,
            v_template_l2.sort_order,
            p_tenant_type,
            p_tenant_id
        );
    END LOOP;

    UPDATE expenses e
    SET
        category_node_id = (v_code_map ->> e.category_node_id::text)::uuid,
        category_l1_id = (v_code_map ->> e.category_l1_id::text)::uuid,
        category_l2_id = CASE
            WHEN e.category_l2_id IS NULL THEN NULL
            ELSE (v_code_map ->> e.category_l2_id::text)::uuid
        END
    WHERE e.tenant_type = p_tenant_type
      AND e.tenant_id = p_tenant_id
      AND e.deleted_at IS NULL;
END;
$$;

CREATE OR REPLACE FUNCTION delete_category_with_transfer(
    p_node_id uuid,
    p_transfer_to_id uuid DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_node category_nodes%ROWTYPE;
    v_target category_nodes%ROWTYPE;
    v_expense_count int;
    v_affected int := 0;
    v_l1_count int;
    v_child_ids uuid[];
BEGIN
    SELECT * INTO v_node FROM category_nodes WHERE id = p_node_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'category not found';
    END IF;

    IF v_node.tenant_type IS NULL THEN
        RAISE EXCEPTION 'cannot delete template category';
    END IF;

    IF NOT can_access_tenant(v_node.tenant_type, v_node.tenant_id) THEN
        RAISE EXCEPTION 'access denied';
    END IF;

    IF v_node.code = 'unknown' THEN
        RAISE EXCEPTION 'cannot delete unknown category';
    END IF;

    IF v_node.level = 1 THEN
        SELECT count(*) INTO v_l1_count
        FROM category_nodes
        WHERE tenant_type = v_node.tenant_type
          AND tenant_id = v_node.tenant_id
          AND level = 1;
        IF v_l1_count <= 1 THEN
            RAISE EXCEPTION 'cannot delete last L1 category';
        END IF;
        SELECT array_agg(id) INTO v_child_ids
        FROM category_nodes
        WHERE parent_id = v_node.id;
    END IF;

    SELECT count(*) INTO v_expense_count
    FROM expenses e
    WHERE e.tenant_type = v_node.tenant_type
      AND e.tenant_id = v_node.tenant_id
      AND e.deleted_at IS NULL
      AND (
          e.category_node_id = p_node_id
          OR e.category_l1_id = p_node_id
          OR e.category_l2_id = p_node_id
          OR (v_child_ids IS NOT NULL AND e.category_l2_id = ANY(v_child_ids))
      );

    IF v_expense_count > 0 THEN
        IF p_transfer_to_id IS NULL THEN
            RAISE EXCEPTION 'transfer_required';
        END IF;

        SELECT * INTO v_target FROM category_nodes WHERE id = p_transfer_to_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'transfer target not found';
        END IF;

        IF v_target.tenant_type IS DISTINCT FROM v_node.tenant_type
           OR v_target.tenant_id IS DISTINCT FROM v_node.tenant_id THEN
            RAISE EXCEPTION 'transfer target must be same tenant';
        END IF;

        IF v_target.id = v_node.id THEN
            RAISE EXCEPTION 'transfer target cannot be deleted category';
        END IF;

        IF v_target.level = 1 THEN
            UPDATE expenses e
            SET
                category_node_id = v_target.id,
                assigned_level = 1,
                category_l1_id = v_target.id,
                category_l2_id = NULL,
                category_l3_id = NULL
            WHERE e.tenant_type = v_node.tenant_type
              AND e.tenant_id = v_node.tenant_id
              AND e.deleted_at IS NULL
              AND (
                  e.category_node_id = p_node_id
                  OR e.category_l1_id = p_node_id
                  OR e.category_l2_id = p_node_id
                  OR (v_child_ids IS NOT NULL AND e.category_l2_id = ANY(v_child_ids))
              );
        ELSE
            UPDATE expenses e
            SET
                category_node_id = v_target.id,
                assigned_level = 2,
                category_l1_id = v_target.parent_id,
                category_l2_id = v_target.id,
                category_l3_id = NULL
            WHERE e.tenant_type = v_node.tenant_type
              AND e.tenant_id = v_node.tenant_id
              AND e.deleted_at IS NULL
              AND (
                  e.category_node_id = p_node_id
                  OR e.category_l1_id = p_node_id
                  OR e.category_l2_id = p_node_id
                  OR (v_child_ids IS NOT NULL AND e.category_l2_id = ANY(v_child_ids))
              );
        END IF;
        GET DIAGNOSTICS v_affected = ROW_COUNT;
    END IF;

    IF v_node.level = 1 THEN
        DELETE FROM category_nodes WHERE parent_id = v_node.id;
    END IF;

    DELETE FROM category_nodes WHERE id = p_node_id;

    RETURN jsonb_build_object(
        'deleted_id', p_node_id,
        'transferred_expenses', v_affected
    );
END;
$$;

DROP POLICY IF EXISTS category_nodes_select_authenticated ON category_nodes;

CREATE POLICY category_nodes_select
    ON category_nodes
    FOR SELECT
    TO authenticated
    USING (
        tenant_type IS NULL
        OR can_access_tenant(tenant_type, tenant_id)
    );

CREATE POLICY category_nodes_insert_tenant
    ON category_nodes
    FOR INSERT
    TO authenticated
    WITH CHECK (
        tenant_type IS NOT NULL
        AND tenant_id IS NOT NULL
        AND can_access_tenant(tenant_type, tenant_id)
    );

CREATE POLICY category_nodes_update_tenant
    ON category_nodes
    FOR UPDATE
    TO authenticated
    USING (
        tenant_type IS NOT NULL
        AND can_access_tenant(tenant_type, tenant_id)
    )
    WITH CHECK (
        tenant_type IS NOT NULL
        AND can_access_tenant(tenant_type, tenant_id)
    );

CREATE POLICY category_nodes_delete_tenant
    ON category_nodes
    FOR DELETE
    TO authenticated
    USING (
        tenant_type IS NOT NULL
        AND code <> 'unknown'
        AND can_access_tenant(tenant_type, tenant_id)
    );

GRANT INSERT, UPDATE, DELETE ON category_nodes TO authenticated;
GRANT EXECUTE ON FUNCTION can_access_tenant(text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION ensure_tenant_taxonomy(text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION delete_category_with_transfer(uuid, uuid) TO authenticated;
