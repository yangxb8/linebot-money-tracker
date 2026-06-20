-- Store LINE group/room display names for dashboard tenant switcher (feature 009)

CREATE TABLE IF NOT EXISTS tenant_chats (
    tenant_type text NOT NULL,
    tenant_id text NOT NULL,
    display_name text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_type, tenant_id)
);

INSERT INTO tenant_chats (tenant_type, tenant_id, display_name)
SELECT DISTINCT tenant_type, tenant_id, NULL
FROM tenant_chat_members
ON CONFLICT (tenant_type, tenant_id) DO NOTHING;

ALTER TABLE tenant_chat_members
    ADD CONSTRAINT tenant_chat_members_tenant_fkey
    FOREIGN KEY (tenant_type, tenant_id)
    REFERENCES tenant_chats (tenant_type, tenant_id);

ALTER TABLE tenant_chats ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_chats_select_member
    ON tenant_chats
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM tenant_chat_members tcm
            WHERE tcm.tenant_type = tenant_chats.tenant_type
              AND tcm.tenant_id = tenant_chats.tenant_id
              AND tcm.line_user_id = current_line_user_id()
        )
    );

GRANT SELECT ON tenant_chats TO authenticated;
