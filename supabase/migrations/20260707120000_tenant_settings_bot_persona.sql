-- Extend tenant settings with LINE bot persona configuration.

ALTER TABLE tenant_settings
    ADD COLUMN IF NOT EXISTS bot_persona_preset text,
    ADD COLUMN IF NOT EXISTS bot_persona_custom_text text,
    ADD COLUMN IF NOT EXISTS bot_persona_emoji_level smallint
        CHECK (bot_persona_emoji_level BETWEEN 0 AND 2),
    ADD COLUMN IF NOT EXISTS bot_persona_updated_at timestamptz;

