-- Wish list items (feature 020)
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

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
    executed_expense_id uuid,
    created_by_line_user_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    CONSTRAINT wish_list_executed_chk CHECK (
        deleted_at IS NOT NULL
        OR (status = 'active' AND executed_expense_id IS NULL)
        OR (status = 'executed' AND executed_expense_id IS NOT NULL)
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

ALTER TABLE wish_list_items
    ADD CONSTRAINT wish_list_items_executed_expense_fk
    FOREIGN KEY (executed_expense_id) REFERENCES expenses(id) ON DELETE SET NULL;

ALTER TABLE wish_list_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY wish_list_items_select
    ON wish_list_items FOR SELECT TO authenticated
    USING (
        (tenant_type = 'user' AND tenant_id = current_line_user_id())
        OR (
            tenant_type IN ('group', 'room')
            AND EXISTS (
                SELECT 1 FROM tenant_chat_members tcm
                WHERE tcm.tenant_type = wish_list_items.tenant_type
                  AND tcm.tenant_id = wish_list_items.tenant_id
                  AND tcm.line_user_id = current_line_user_id()
            )
        )
    );

CREATE POLICY wish_list_items_insert
    ON wish_list_items FOR INSERT TO authenticated
    WITH CHECK (
        created_by_line_user_id = current_line_user_id()
        AND (
            (tenant_type = 'user' AND tenant_id = current_line_user_id())
            OR (
                tenant_type IN ('group', 'room')
                AND EXISTS (
                    SELECT 1 FROM tenant_chat_members tcm
                    WHERE tcm.tenant_type = wish_list_items.tenant_type
                      AND tcm.tenant_id = wish_list_items.tenant_id
                      AND tcm.line_user_id = current_line_user_id()
                )
            )
        )
    );

CREATE POLICY wish_list_items_update
    ON wish_list_items FOR UPDATE TO authenticated
    USING (
        (tenant_type = 'user' AND tenant_id = current_line_user_id())
        OR (
            tenant_type IN ('group', 'room')
            AND EXISTS (
                SELECT 1 FROM tenant_chat_members tcm
                WHERE tcm.tenant_type = wish_list_items.tenant_type
                  AND tcm.tenant_id = wish_list_items.tenant_id
                  AND tcm.line_user_id = current_line_user_id()
            )
        )
    )
    WITH CHECK (
        (tenant_type = 'user' AND tenant_id = current_line_user_id())
        OR (
            tenant_type IN ('group', 'room')
            AND EXISTS (
                SELECT 1 FROM tenant_chat_members tcm
                WHERE tcm.tenant_type = wish_list_items.tenant_type
                  AND tcm.tenant_id = wish_list_items.tenant_id
                  AND tcm.line_user_id = current_line_user_id()
            )
        )
    );

CREATE POLICY wish_list_items_delete
    ON wish_list_items FOR DELETE TO authenticated
    USING (
        (tenant_type = 'user' AND tenant_id = current_line_user_id())
        OR (
            tenant_type IN ('group', 'room')
            AND EXISTS (
                SELECT 1 FROM tenant_chat_members tcm
                WHERE tcm.tenant_type = wish_list_items.tenant_type
                  AND tcm.tenant_id = wish_list_items.tenant_id
                  AND tcm.line_user_id = current_line_user_id()
            )
        )
    );

GRANT SELECT, INSERT, UPDATE, DELETE ON wish_list_items TO authenticated;
GRANT ALL ON wish_list_items TO service_role;
