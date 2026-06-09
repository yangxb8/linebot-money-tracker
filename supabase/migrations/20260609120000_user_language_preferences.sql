CREATE TABLE IF NOT EXISTS user_language_preferences (
    line_user_id text PRIMARY KEY,
    reply_language text NOT NULL DEFAULT 'ja' CHECK (reply_language IN ('ja', 'en', 'zh')),
    source text NOT NULL DEFAULT 'default' CHECK (source IN ('default', 'line_profile', 'user_request')),
    line_profile_language text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_language_preferences_updated
    ON user_language_preferences (updated_at DESC);
