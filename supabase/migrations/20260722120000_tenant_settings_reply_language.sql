-- Tenant setting: optional LINE bot reply language override.
-- NULL = Default (system / LINE profile language resolution).

ALTER TABLE tenant_settings
    ADD COLUMN IF NOT EXISTS reply_language text
        CHECK (reply_language IS NULL OR reply_language IN ('en', 'ja', 'zh'));
