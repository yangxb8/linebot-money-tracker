# Contract: Supabase Schema Delta

**Feature**: 009-expense-web-dashboard  
**Migration**: `supabase/migrations/20260619120000_web_dashboard_auth_rls.sql`

## Table: line_auth_identities

```sql
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
```

No `INSERT`/`UPDATE`/`DELETE` policies for `authenticated` — writes via service role in Next.js Route Handlers only.

## Function: current_line_user_id

```sql
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
```

## RLS: expenses (SELECT for authenticated)

```sql
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
```

Existing service-role bot writes unchanged (bypass RLS).

## RLS: tenant_chat_members (SELECT own rows)

```sql
CREATE POLICY tenant_chat_members_select_own
    ON tenant_chat_members
    FOR SELECT
    TO authenticated
    USING (line_user_id = current_line_user_id());
```

## RLS: user_language_preferences (SELECT own row)

```sql
CREATE POLICY user_language_preferences_select_own
    ON user_language_preferences
    FOR SELECT
    TO authenticated
    USING (line_user_id = current_line_user_id());
```

## RLS: category_nodes (read taxonomy)

```sql
CREATE POLICY category_nodes_select_authenticated
    ON category_nodes
    FOR SELECT
    TO authenticated
    USING (true);
```

## View: v_expenses_enriched

Ensure `authenticated` role can `SELECT` the view (inherits `expenses` RLS when `security_invoker` is on, or add explicit grant):

```sql
GRANT SELECT ON v_expenses_enriched TO authenticated;
GRANT SELECT ON category_nodes TO authenticated;
GRANT SELECT ON tenant_chat_members TO authenticated;
GRANT SELECT ON user_language_preferences TO authenticated;
```

If view uses `security_barrier` / definer semantics, verify with:

```sql
-- As authenticated user via Supabase client only
SELECT id FROM v_expenses_enriched LIMIT 1;
```

Adjust view to `security_invoker = true` (Postgres 15+) if needed so RLS on `expenses` applies.

## Rollback notes

Drop policies before dropping `line_auth_identities`. Bot operation does not depend on this table.
