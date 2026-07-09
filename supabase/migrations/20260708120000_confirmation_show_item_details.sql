-- Tenant setting: show per-item lines in LINE expense confirmations.

ALTER TABLE tenant_settings
    ADD COLUMN IF NOT EXISTS confirmation_show_item_details boolean NOT NULL DEFAULT false;
