-- Web dashboard auth bridge and RLS (feature 009)
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

CREATE TABLE IF NOT EXISTS line_auth_identities (
    auth_user_id uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    line_user_id text NOT NULL UNIQUE,
    display_name text,
    picture_url text,
    linked_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_line_auth_identities_line_user
    ON line_auth_identities (line_user_id);

ALTER TABLE line_auth_identities ENABLE ROW LEVEL SECURITY;

CREATE POLICY line_auth_identities_select_own
    ON line_auth_identities
    FOR SELECT
    TO authenticated
    USING (auth_user_id = auth.uid());

CREATE OR REPLACE FUNCTION current_line_user_id()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT line_user_id
  FROM line_auth_identities
  WHERE auth_user_id = auth.uid()
$$;

CREATE POLICY expenses_select_authenticated
    ON expenses
    FOR SELECT
    TO authenticated
    USING (
        (
            tenant_type = 'user'
            AND tenant_id = current_line_user_id()
        )
        OR (
            tenant_type IN ('group', 'room')
            AND EXISTS (
                SELECT 1
                FROM tenant_chat_members tcm
                WHERE tcm.tenant_type = expenses.tenant_type
                  AND tcm.tenant_id = expenses.tenant_id
                  AND tcm.line_user_id = current_line_user_id()
            )
        )
    );

ALTER TABLE tenant_chat_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_chat_members_select_own
    ON tenant_chat_members
    FOR SELECT
    TO authenticated
    USING (line_user_id = current_line_user_id());

ALTER TABLE user_language_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_language_preferences_select_own
    ON user_language_preferences
    FOR SELECT
    TO authenticated
    USING (line_user_id = current_line_user_id());

ALTER TABLE category_nodes ENABLE ROW LEVEL SECURITY;

CREATE POLICY category_nodes_select_authenticated
    ON category_nodes
    FOR SELECT
    TO authenticated
    USING (true);

GRANT SELECT ON v_expenses_enriched TO authenticated;
GRANT SELECT ON category_nodes TO authenticated;
GRANT SELECT ON tenant_chat_members TO authenticated;
GRANT SELECT ON user_language_preferences TO authenticated;
GRANT SELECT ON line_auth_identities TO authenticated;

ALTER VIEW v_expenses_enriched SET (security_invoker = true);

REVOKE EXECUTE ON FUNCTION current_line_user_id() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION current_line_user_id() FROM anon;
REVOKE EXECUTE ON FUNCTION current_line_user_id() FROM authenticated;
