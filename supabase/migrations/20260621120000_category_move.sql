-- Category drag-and-drop: reparent L2, promote L2→L1, demote L1→L2 (feature 010)

CREATE OR REPLACE FUNCTION move_category(
    p_node_id uuid,
    p_new_level smallint,
    p_new_parent_id uuid DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_node category_nodes%ROWTYPE;
    v_parent category_nodes%ROWTYPE;
    v_child_count int;
    v_new_sort int;
BEGIN
    SELECT * INTO v_node FROM category_nodes WHERE id = p_node_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'category not found';
    END IF;

    IF v_node.tenant_type IS NULL THEN
        RAISE EXCEPTION 'cannot move template category';
    END IF;

    IF NOT can_access_tenant(v_node.tenant_type, v_node.tenant_id) THEN
        RAISE EXCEPTION 'access denied';
    END IF;

    IF v_node.code = 'unknown' THEN
        RAISE EXCEPTION 'cannot move unknown category';
    END IF;

    IF p_new_level NOT IN (1, 2) THEN
        RAISE EXCEPTION 'invalid level';
    END IF;

    -- Promote L2 → L1
    IF v_node.level = 2 AND p_new_level = 1 THEN
        IF p_new_parent_id IS NOT NULL THEN
            RAISE EXCEPTION 'parent must be null when promoting to L1';
        END IF;

        SELECT coalesce(max(sort_order), 0) + 1 INTO v_new_sort
        FROM category_nodes
        WHERE tenant_type = v_node.tenant_type
          AND tenant_id = v_node.tenant_id
          AND level = 1;

        UPDATE category_nodes
        SET level = 1, parent_id = NULL, sort_order = v_new_sort
        WHERE id = p_node_id;

        UPDATE expenses e
        SET
            assigned_level = 1,
            category_node_id = p_node_id,
            category_l1_id = p_node_id,
            category_l2_id = NULL,
            category_l3_id = NULL
        WHERE e.tenant_type = v_node.tenant_type
          AND e.tenant_id = v_node.tenant_id
          AND e.deleted_at IS NULL
          AND (
              e.category_node_id = p_node_id
              OR e.category_l2_id = p_node_id
          );

        RETURN jsonb_build_object('id', p_node_id, 'level', 1, 'parent_id', NULL);

    -- Reparent L2 → L2 under another L1
    ELSIF v_node.level = 2 AND p_new_level = 2 THEN
        IF p_new_parent_id IS NULL THEN
            RAISE EXCEPTION 'parent required for L2';
        END IF;

        IF p_new_parent_id = v_node.parent_id THEN
            RAISE EXCEPTION 'already under this parent';
        END IF;

        SELECT * INTO v_parent FROM category_nodes WHERE id = p_new_parent_id;
        IF NOT FOUND OR v_parent.level <> 1 THEN
            RAISE EXCEPTION 'invalid parent';
        END IF;

        IF v_parent.tenant_type IS DISTINCT FROM v_node.tenant_type
           OR v_parent.tenant_id IS DISTINCT FROM v_node.tenant_id THEN
            RAISE EXCEPTION 'parent must be same tenant';
        END IF;

        IF v_parent.code = 'unknown' THEN
            RAISE EXCEPTION 'cannot move under unknown category';
        END IF;

        SELECT coalesce(max(sort_order), 0) + 1 INTO v_new_sort
        FROM category_nodes
        WHERE tenant_type = v_node.tenant_type
          AND tenant_id = v_node.tenant_id
          AND parent_id = p_new_parent_id;

        UPDATE category_nodes
        SET parent_id = p_new_parent_id, sort_order = v_new_sort
        WHERE id = p_node_id;

        UPDATE expenses e
        SET category_l1_id = p_new_parent_id
        WHERE e.tenant_type = v_node.tenant_type
          AND e.tenant_id = v_node.tenant_id
          AND e.deleted_at IS NULL
          AND (
              e.category_node_id = p_node_id
              OR e.category_l2_id = p_node_id
          );

        RETURN jsonb_build_object('id', p_node_id, 'level', 2, 'parent_id', p_new_parent_id);

    -- Demote L1 → L2 (only when no L2 children)
    ELSIF v_node.level = 1 AND p_new_level = 2 THEN
        IF p_new_parent_id IS NULL THEN
            RAISE EXCEPTION 'parent required when demoting to L2';
        END IF;

        SELECT count(*) INTO v_child_count
        FROM category_nodes
        WHERE parent_id = p_node_id;

        IF v_child_count > 0 THEN
            RAISE EXCEPTION 'cannot demote L1 with subcategories';
        END IF;

        SELECT * INTO v_parent FROM category_nodes WHERE id = p_new_parent_id;
        IF NOT FOUND OR v_parent.level <> 1 THEN
            RAISE EXCEPTION 'invalid parent';
        END IF;

        IF v_parent.tenant_type IS DISTINCT FROM v_node.tenant_type
           OR v_parent.tenant_id IS DISTINCT FROM v_node.tenant_id THEN
            RAISE EXCEPTION 'parent must be same tenant';
        END IF;

        IF v_parent.code = 'unknown' THEN
            RAISE EXCEPTION 'cannot move under unknown category';
        END IF;

        IF p_new_parent_id = p_node_id THEN
            RAISE EXCEPTION 'cannot demote under self';
        END IF;

        SELECT coalesce(max(sort_order), 0) + 1 INTO v_new_sort
        FROM category_nodes
        WHERE tenant_type = v_node.tenant_type
          AND tenant_id = v_node.tenant_id
          AND parent_id = p_new_parent_id;

        UPDATE category_nodes
        SET level = 2, parent_id = p_new_parent_id, sort_order = v_new_sort
        WHERE id = p_node_id;

        UPDATE expenses e
        SET
            assigned_level = 2,
            category_node_id = p_node_id,
            category_l1_id = p_new_parent_id,
            category_l2_id = p_node_id,
            category_l3_id = NULL
        WHERE e.tenant_type = v_node.tenant_type
          AND e.tenant_id = v_node.tenant_id
          AND e.deleted_at IS NULL
          AND (
              e.category_node_id = p_node_id
              OR e.category_l1_id = p_node_id
          );

        RETURN jsonb_build_object('id', p_node_id, 'level', 2, 'parent_id', p_new_parent_id);
    ELSE
        RAISE EXCEPTION 'invalid move';
    END IF;
END;
$$;

GRANT EXECUTE ON FUNCTION move_category(uuid, smallint, uuid) TO authenticated;
