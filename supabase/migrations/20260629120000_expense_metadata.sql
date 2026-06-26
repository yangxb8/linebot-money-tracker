-- Expense metadata jsonb for receipt store_name (feature 014)
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}';
