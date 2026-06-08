-- Allow reply-to on follow-up bot messages (e.g. delete-all YES prompt)
ALTER TABLE confirmation_messages
    ADD COLUMN IF NOT EXISTS interaction_bot_message_id text;

UPDATE confirmation_messages
SET interaction_bot_message_id = bot_message_id
WHERE interaction_bot_message_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_confirmation_messages_interaction
    ON confirmation_messages (tenant_type, tenant_id, interaction_bot_message_id)
    WHERE interaction_bot_message_id IS NOT NULL;
