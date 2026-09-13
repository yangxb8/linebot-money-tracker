-- Optional per-category "spending too fast" (pace-ahead) alerts for the LINE bot.
-- Over-budget warnings remain always-on; pace-ahead defaults to off.

ALTER TABLE category_nodes
    ADD COLUMN IF NOT EXISTS pace_warning_enabled boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN category_nodes.pace_warning_enabled IS
    'When true, LINE bot may prepend a pace-ahead (spending too fast) warning for this category budget. Over-budget warnings ignore this flag and always fire.';
