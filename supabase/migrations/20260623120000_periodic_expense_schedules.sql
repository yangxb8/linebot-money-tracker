-- Periodic expense schedules (feature 011)
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

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

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS periodic_schedule_id uuid
        REFERENCES periodic_expense_schedules(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX IF NOT EXISTS expenses_periodic_occurrence_uq
    ON expenses (periodic_schedule_id, expense_date)
    WHERE periodic_schedule_id IS NOT NULL AND deleted_at IS NULL;

-- Pause schedules when tenant category is deleted
CREATE OR REPLACE FUNCTION pause_periodic_schedules_on_category_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
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

DROP TRIGGER IF EXISTS trg_pause_periodic_on_category_delete ON category_nodes;
CREATE TRIGGER trg_pause_periodic_on_category_delete
    BEFORE DELETE ON category_nodes
    FOR EACH ROW EXECUTE FUNCTION pause_periodic_schedules_on_category_delete();

-- Process one occurrence atomically
CREATE OR REPLACE FUNCTION process_periodic_occurrence(
    p_schedule_id uuid,
    p_occurrence_date date,
    p_next_run_date date,
    p_end boolean,
    p_skip_occurrence boolean DEFAULT false
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    s periodic_expense_schedules%ROWTYPE;
    v_source_message_id text;
    v_inserted int := 0;
BEGIN
    SELECT * INTO s
    FROM periodic_expense_schedules
    WHERE id = p_schedule_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('inserted', 0, 'skipped', 1, 'reason', 'not_found');
    END IF;

    IF s.status <> 'active' OR s.next_run_date IS DISTINCT FROM p_occurrence_date THEN
        RETURN jsonb_build_object('inserted', 0, 'skipped', 1, 'reason', 'not_due');
    END IF;

    IF p_skip_occurrence THEN
        UPDATE periodic_expense_schedules
        SET status = 'ended',
            next_run_date = NULL,
            updated_at = now()
        WHERE id = s.id;
        RETURN jsonb_build_object('inserted', 0, 'skipped', 0, 'ended', true);
    END IF;

    v_source_message_id := 'periodic:' || s.id::text || ':' || p_occurrence_date::text;

    INSERT INTO expenses (
        tenant_type,
        tenant_id,
        logged_by_line_user_id,
        line_user_id,
        source_message_id,
        line_item_index,
        description,
        amount,
        currency,
        expense_date,
        category_node_id,
        assigned_level,
        category_l1_id,
        category_l2_id,
        periodic_schedule_id
    ) VALUES (
        s.tenant_type,
        s.tenant_id,
        s.created_by_line_user_id,
        s.created_by_line_user_id,
        v_source_message_id,
        0,
        s.name,
        s.amount,
        s.currency,
        p_occurrence_date,
        s.category_node_id,
        s.assigned_level,
        s.category_l1_id,
        s.category_l2_id,
        s.id
    )
    ON CONFLICT DO NOTHING;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    IF v_inserted > 0 THEN
        UPDATE periodic_expense_schedules
        SET occurrence_count = occurrence_count + 1,
            cumulative_amount = cumulative_amount + s.amount,
            next_run_date = CASE WHEN p_end THEN NULL ELSE p_next_run_date END,
            status = CASE WHEN p_end THEN 'ended' ELSE 'active' END,
            updated_at = now()
        WHERE id = s.id;
    ELSE
        -- Idempotent skip: still advance if duplicate expense exists for this date
        UPDATE periodic_expense_schedules
        SET next_run_date = CASE WHEN p_end THEN NULL ELSE p_next_run_date END,
            status = CASE WHEN p_end THEN 'ended' ELSE status END,
            updated_at = now()
        WHERE id = s.id;
    END IF;

    RETURN jsonb_build_object(
        'inserted', v_inserted,
        'skipped', CASE WHEN v_inserted = 0 THEN 1 ELSE 0 END,
        'ended', p_end
    );
END;
$$;

-- Batch processor: p_actions jsonb array of {schedule_id, occurrence_date, next_run_date, end}
CREATE OR REPLACE FUNCTION process_due_periodic_schedules(
    p_actions jsonb DEFAULT '[]'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    action jsonb;
    result jsonb;
    v_processed int := 0;
    v_inserted int := 0;
    v_skipped int := 0;
    v_ended int := 0;
BEGIN
    FOR action IN SELECT * FROM jsonb_array_elements(p_actions)
    LOOP
        result := process_periodic_occurrence(
            (action->>'schedule_id')::uuid,
            (action->>'occurrence_date')::date,
            NULLIF(action->>'next_run_date', '')::date,
            COALESCE((action->>'end')::boolean, false),
            COALESCE((action->>'skip_occurrence')::boolean, false)
        );
        v_processed := v_processed + 1;
        v_inserted := v_inserted + COALESCE((result->>'inserted')::int, 0);
        v_skipped := v_skipped + COALESCE((result->>'skipped')::int, 0);
        IF COALESCE((result->>'ended')::boolean, false) THEN
            v_ended := v_ended + 1;
        END IF;
    END LOOP;

    RETURN jsonb_build_object(
        'processed', v_processed,
        'inserted', v_inserted,
        'skipped', v_skipped,
        'ended', v_ended
    );
END;
$$;

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
    WITH CHECK (
        created_by_line_user_id = current_line_user_id()
        AND (
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
        )
    );

CREATE POLICY periodic_schedules_update
    ON periodic_expense_schedules FOR UPDATE TO authenticated
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
    )
    WITH CHECK (
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

CREATE POLICY periodic_schedules_delete
    ON periodic_expense_schedules FOR DELETE TO authenticated
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

GRANT EXECUTE ON FUNCTION process_periodic_occurrence(uuid, date, date, boolean, boolean) TO service_role;
GRANT EXECUTE ON FUNCTION process_due_periodic_schedules(jsonb) TO service_role;
