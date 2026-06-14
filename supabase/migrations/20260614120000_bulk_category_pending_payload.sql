-- Bulk category change: store pending intent/options on confirmation_messages
ALTER TABLE confirmation_messages
    ADD COLUMN IF NOT EXISTS pending_payload jsonb;
