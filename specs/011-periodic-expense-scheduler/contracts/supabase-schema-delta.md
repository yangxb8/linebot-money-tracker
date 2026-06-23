# Supabase Schema Delta: Periodic Expense Scheduler

**Feature**: 011-periodic-expense-scheduler

## periodic_expense_schedules (new table)

```sql
CREATE TABLE periodic_expense_schedules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_type text NOT NULL CHECK (tenant_type IN ('user', 'group', 'room')),
    tenant_id text NOT NULL,
    name text NOT NULL CHECK (char_length(trim(name)) > 0),
    amount numeric(14, 2) NOT NULL CHECK (amount > 0),
    currency char(3) NOT NULL DEFAULT 'JPY',
    assigned_level smallint NOT NULL CHECK (assigned_level IN (1, 2)),
    category_node_id uuid NOT NULL REFERENCES category_nodes(id),
    category_l1_id uuid NOT NULL REFERENCES category_nodes(id),
    category_l2_id uuid REFERENCES category_nodes(id),
    recurrence jsonb NOT NULL,
    start_date date NOT NULL,
    timezone text NOT NULL DEFAULT 'Asia/Tokyo',
    end_kind text NOT NULL CHECK (end_kind IN ('never', 'on_date', 'amount_cap', 'repeat_count')),
    end_date date,
    end_amount_cap numeric(14, 2),
    end_repeat_limit int,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'ended')),
    pause_reason text,
    next_run_date date,
    occurrence_count int NOT NULL DEFAULT 0,
    cumulative_amount numeric(14, 2) NOT NULL DEFAULT 0,
    created_by_line_user_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT periodic_schedules_end_fields_chk CHECK (
        (end_kind = 'never')
        OR (end_kind = 'on_date' AND end_date IS NOT NULL)
        OR (end_kind = 'amount_cap' AND end_amount_cap IS NOT NULL)
        OR (end_kind = 'repeat_count' AND end_repeat_limit IS NOT NULL)
    )
);

CREATE INDEX periodic_schedules_tenant_idx
    ON periodic_expense_schedules (tenant_type, tenant_id);

CREATE INDEX periodic_schedules_due_idx
    ON periodic_expense_schedules (next_run_date)
    WHERE status = 'active';
```

## expenses — link to schedule

```sql
ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS periodic_schedule_id uuid
        REFERENCES periodic_expense_schedules(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX IF NOT EXISTS expenses_periodic_occurrence_uq
    ON expenses (periodic_schedule_id, expense_date)
    WHERE periodic_schedule_id IS NOT NULL AND deleted_at IS NULL;
```

## RLS: periodic_expense_schedules

```sql
ALTER TABLE periodic_expense_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY periodic_schedules_select
    ON periodic_expense_schedules FOR SELECT TO authenticated
    USING (
        (tenant_type = 'user' AND tenant_id = current_line_user_id())
        OR (
            tenant_type IN ('group', 'room')
            AND EXISTS (
                SELECT 1 FROM tenant_chat_members tcm
                WHERE tcm.tenant_type = periodic_expense_schedules.tenant_type
                  AND tcm.tenant_id = periodic_expense_schedules.tenant_id
                  AND tcm.line_user_id = current_line_user_id()
            )
        )
    );

CREATE POLICY periodic_schedules_insert
    ON periodic_expense_schedules FOR INSERT TO authenticated
    WITH CHECK (/* same access + created_by_line_user_id = current_line_user_id() */);

CREATE POLICY periodic_schedules_update
    ON periodic_expense_schedules FOR UPDATE TO authenticated
    USING (/* tenant access */) WITH CHECK (/* tenant access */);

CREATE POLICY periodic_schedules_delete
    ON periodic_expense_schedules FOR DELETE TO authenticated
    USING (/* tenant access */);
```

## Trigger: pause on category delete

```sql
CREATE OR REPLACE FUNCTION pause_periodic_schedules_on_category_delete()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.tenant_type IS NOT NULL THEN
        UPDATE periodic_expense_schedules
        SET status = 'paused',
            pause_reason = 'category_missing',
            updated_at = now()
        WHERE status = 'active'
          AND tenant_type = OLD.tenant_type
          AND tenant_id = OLD.tenant_id
          AND (
              category_node_id = OLD.id
              OR category_l1_id = OLD.id
              OR category_l2_id = OLD.id
          );
    END IF;
    RETURN OLD;
END;
$$;

CREATE TRIGGER trg_pause_periodic_on_category_delete
    BEFORE DELETE ON category_nodes
    FOR EACH ROW EXECUTE FUNCTION pause_periodic_schedules_on_category_delete();
```

## RPC: process_due_periodic_schedules

```sql
CREATE OR REPLACE FUNCTION process_due_periodic_schedules(
    p_as_of timestamptz DEFAULT now()
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
-- Loop active schedules where next_run_date <= local today
-- End checks, insert expense, update counters, advance next_run_date or end
-- Return stats jsonb
$$;
```

**Grant**: `GRANT EXECUTE ON FUNCTION process_due_periodic_schedules(timestamptz) TO service_role;`  
(Called only from cron route with service role key — not exposed to `authenticated`.)

## Environment variables (new)

| Variable | Where | Purpose |
| -------- | ----- | ------- |
| `CRON_SECRET` | Vercel | Authorize cron route |
| `SUPABASE_SERVICE_ROLE_KEY` | Vercel (existing) | Invoke processing RPC |

## Rollback

1. Drop trigger and RPC.
2. Drop `expenses.periodic_schedule_id` column and index.
3. Drop `periodic_expense_schedules` table and policies.
