-- Expense storage schema for linebot-money-tracker (feature 004)
-- Target: https://nyuenufldaqsjybjhawl.supabase.co

CREATE TABLE IF NOT EXISTS category_nodes (
    id uuid PRIMARY KEY,
    code text UNIQUE NOT NULL,
    name_ja text NOT NULL,
    level smallint NOT NULL CHECK (level BETWEEN 1 AND 3),
    parent_id uuid REFERENCES category_nodes (id),
    sort_order int NOT NULL DEFAULT 0,
    CHECK (
        (level = 1 AND parent_id IS NULL)
        OR (level > 1 AND parent_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS expenses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    line_user_id text NOT NULL,
    source_message_id text NOT NULL,
    line_item_index int NOT NULL DEFAULT 0,
    description text NOT NULL,
    amount numeric(14, 2) NOT NULL,
    currency char(3) NOT NULL,
    expense_date date NOT NULL,
    category_node_id uuid NOT NULL REFERENCES category_nodes (id),
    assigned_level smallint NOT NULL CHECK (assigned_level BETWEEN 1 AND 3),
    category_l1_id uuid NOT NULL REFERENCES category_nodes (id),
    category_l2_id uuid REFERENCES category_nodes (id),
    category_l3_id uuid REFERENCES category_nodes (id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (line_user_id, source_message_id, line_item_index)
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date
    ON expenses (line_user_id, expense_date);

CREATE INDEX IF NOT EXISTS idx_expenses_user_l1_date
    ON expenses (line_user_id, category_l1_id, expense_date);

CREATE INDEX IF NOT EXISTS idx_expenses_user_message
    ON expenses (line_user_id, source_message_id);

CREATE TABLE IF NOT EXISTS monthly_budgets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    line_user_id text NOT NULL,
    category_node_id uuid NOT NULL REFERENCES category_nodes (id),
    budget_month date NOT NULL,
    amount numeric(14, 2) NOT NULL,
    currency char(3) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (line_user_id, category_node_id, budget_month, currency)
);

ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_budgets ENABLE ROW LEVEL SECURITY;

-- Seed taxonomy (uuid5 namespace f47ac10b-58cc-4372-a567-0e02b2c3d479 + code)
INSERT INTO category_nodes (id, code, name_ja, level, parent_id, sort_order) VALUES
    ('249350c8-4b24-5117-a515-9ef3988701de', 'food', '食費', 1, NULL, 1),
    ('260c41e8-084c-578b-8861-1c2dd5a34945', 'food.grocery', '食料品', 2, '249350c8-4b24-5117-a515-9ef3988701de', 1),
    ('02d581f8-33fd-514b-b6a7-47955de12b86', 'food.dining', '外食', 2, '249350c8-4b24-5117-a515-9ef3988701de', 2),
    ('f3a68bb0-7566-5180-8e15-e98ac2ec9e00', 'food.dining.cafe', 'カフェ', 3, '02d581f8-33fd-514b-b6a7-47955de12b86', 1),
    ('e13663f3-da25-5b57-90bf-61d84a4dabbf', 'food.dining.restaurant', 'レストラン', 3, '02d581f8-33fd-514b-b6a7-47955de12b86', 2),
    ('14ed322f-86f2-5775-af4e-dd09b033c88e', 'food.dining.fastfood', 'ファストフード', 3, '02d581f8-33fd-514b-a6a7-47955de12b86', 3),
    ('dbdcf863-48d5-5a67-8b2a-56803dd02c67', 'food.lunch', '昼食・給食', 2, '249350c8-4b24-5117-a515-9ef3988701de', 3),
    ('5e19a511-90c0-55e9-a710-c1ee71fdb002', 'housing', '住居', 1, NULL, 2),
    ('762e8bbe-3a7b-5a39-8121-a1ca377b7697', 'housing.rent', '家賃', 2, '5e19a511-90c0-55e9-a710-c1ee71fdb002', 1),
    ('6e5d4917-0bc2-5bd7-aff7-9f5bcfad6a05', 'housing.mortgage', '住宅ローン', 2, '5e19a511-90c0-55e9-a710-c1ee71fdb002', 2),
    ('60e5f112-1ad7-570b-85e5-1bf0b7a975ab', 'utilities', '光熱・通信', 1, NULL, 3),
    ('42c2409d-9e9c-5348-a51d-d37496edeca7', 'utilities.electric', '電気', 2, '60e5f112-1ad7-570b-85e5-1bf0b7a975ab', 1),
    ('de30b37d-d6db-5e36-a40e-101043a3d004', 'utilities.gas', 'ガス', 2, '60e5f112-1ad7-570b-85e5-1bf0b7a975ab', 2),
    ('6e5130ec-e4a0-54e0-b484-926d054fed58', 'utilities.water', '水道', 2, '60e5f112-1ad7-570b-85e5-1bf0b7a975ab', 3),
    ('54dec857-6e7b-55bd-9de0-aef391256c6f', 'utilities.telecom', '通信費', 2, '60e5f112-1ad7-570b-85e5-1bf0b7a975ab', 4),
    ('171920a3-e860-5c94-baf2-7b9bb2065a11', 'transport', '交通', 1, NULL, 4),
    ('be5d81d0-5759-5dd2-ad30-20d1c49e52ca', 'transport.transit', '公共交通', 2, '171920a3-e860-5c94-baf2-7b9bb2065a11', 1),
    ('77d1a54d-7781-5afc-9b05-74953285295c', 'transport.fuel', 'ガソリン', 2, '171920a3-e860-5c94-baf2-7b9bb2065a11', 2),
    ('d020a53f-4bb8-5357-bf45-68c0835e8dd6', 'transport.car', '自動車', 2, '171920a3-e860-5c94-baf2-7b9bb2065a11', 3),
    ('343cc790-d73c-5d29-ae4c-a3de483c611e', 'healthcare', '医療・健康', 1, NULL, 5),
    ('0a94d981-fe41-51e6-a250-688ed492783f', 'healthcare.medical', '医療費', 2, '343cc790-d73c-5d29-ae4c-a3de483c611e', 1),
    ('184a553c-e3d7-5305-8662-281fe73b9d42', 'healthcare.pharmacy', '薬局', 2, '343cc790-d73c-5d29-ae4c-a3de483c611e', 2),
    ('79771b27-1395-5bb4-b626-8aae8c619b13', 'education', '教育・子ども', 1, NULL, 6),
    ('2886fba6-c862-5bec-a7ea-a309a66a1c1c', 'education.tuition', '学費', 2, '79771b27-1395-5bb4-b626-8aae8c619b13', 1),
    ('924f9e06-c699-5a0c-98ff-61e8fa51445e', 'education.lessons', '習い事', 2, '79771b27-1395-5bb4-b626-8aae8c619b13', 2),
    ('9402c910-3548-5e4a-b7fe-ec32ee53719e', 'clothing', '被服・美容', 1, NULL, 7),
    ('f6d1ebce-c926-5cd2-9b71-c6b8ff04af59', 'clothing.apparel', '衣類', 2, '9402c910-3548-5e4a-b7fe-ec32ee53719e', 1),
    ('0db531d8-37fc-50ea-857c-1cede2825ce7', 'clothing.beauty', '美容', 2, '9402c910-3548-5e4a-b7fe-ec32ee53719e', 2),
    ('75b18813-765d-5f69-92a3-1156dd26137a', 'leisure', '娯楽・交際', 1, NULL, 8),
    ('287c077f-0e58-51bb-9611-f526d575051a', 'leisure.entertainment', '娯楽', 2, '75b18813-765d-5f69-92a3-1156dd26137a', 1),
    ('c4e44662-b7db-5198-9768-d86a74b0a1e0', 'leisure.social', '交際費', 2, '75b18813-765d-5f69-92a3-1156dd26137a', 2),
    ('46f8be43-ccae-540b-9781-38001ecabd51', 'leisure.travel', '旅行', 2, '75b18813-765d-5f69-92a3-1156dd26137a', 3),
    ('f0401197-24d4-564d-bdfd-f05a82fe0875', 'personal', '嗜好品', 1, NULL, 9),
    ('dd3edeaa-ef3d-5f23-8214-da12bb605599', 'personal.tobacco_alcohol', 'タバコ・お酒', 2, 'f0401197-24d4-564d-bdfd-f05a82fe0875', 1),
    ('a87bf5f8-9909-507e-858a-8a86c43f5205', 'personal.hobby', '趣味', 2, 'f0401197-24d4-564d-bdfd-f05a82fe0875', 2),
    ('89a026f7-4dc0-590c-9c8e-81c822370c10', 'finance', '金融・保険', 1, NULL, 10),
    ('fb8e172f-b675-5bf2-97e6-59f23c21df3f', 'finance.fees', '手数料', 2, '89a026f7-4dc0-590c-9c8e-81c822370c10', 1),
    ('80fd089f-a131-5819-9674-34846ede4066', 'finance.insurance', '保険', 2, '89a026f7-4dc0-590c-9c8e-81c822370c10', 2),
    ('9b504567-4a2e-54be-825d-0e81c43924ff', 'unknown', '不明', 1, NULL, 99)
ON CONFLICT (code) DO NOTHING;

CREATE OR REPLACE FUNCTION monthly_expense_total(
    p_line_user_id text,
    p_year int,
    p_month int,
    p_category_node_id uuid,
    p_currency char(3)
) RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    cat_level smallint;
    total numeric;
BEGIN
    SELECT level INTO cat_level FROM category_nodes WHERE id = p_category_node_id;
    IF cat_level IS NULL THEN
        RETURN 0;
    END IF;

    SELECT COALESCE(SUM(amount), 0) INTO total
    FROM expenses e
    WHERE e.line_user_id = p_line_user_id
      AND e.currency = p_currency
      AND EXTRACT(YEAR FROM e.expense_date) = p_year
      AND EXTRACT(MONTH FROM e.expense_date) = p_month
      AND (
          (cat_level = 1 AND (
              (e.assigned_level = 1 AND e.category_node_id = p_category_node_id)
              OR (e.assigned_level > 1 AND e.category_l1_id = p_category_node_id)
          ))
          OR (cat_level = 2 AND (
              (e.assigned_level = 2 AND e.category_node_id = p_category_node_id)
              OR (e.assigned_level = 3 AND e.category_l2_id = p_category_node_id)
          ))
          OR (cat_level = 3 AND e.assigned_level = 3 AND e.category_node_id = p_category_node_id)
      );

    RETURN total;
END;
$$;

CREATE OR REPLACE FUNCTION yearly_expense_total(
    p_line_user_id text,
    p_year int,
    p_category_node_id uuid,
    p_currency char(3)
) RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    cat_level smallint;
    total numeric;
BEGIN
    SELECT level INTO cat_level FROM category_nodes WHERE id = p_category_node_id;
    IF cat_level IS NULL THEN
        RETURN 0;
    END IF;

    SELECT COALESCE(SUM(amount), 0) INTO total
    FROM expenses e
    WHERE e.line_user_id = p_line_user_id
      AND e.currency = p_currency
      AND EXTRACT(YEAR FROM e.expense_date) = p_year
      AND (
          (cat_level = 1 AND (
              (e.assigned_level = 1 AND e.category_node_id = p_category_node_id)
              OR (e.assigned_level > 1 AND e.category_l1_id = p_category_node_id)
          ))
          OR (cat_level = 2 AND (
              (e.assigned_level = 2 AND e.category_node_id = p_category_node_id)
              OR (e.assigned_level = 3 AND e.category_l2_id = p_category_node_id)
          ))
          OR (cat_level = 3 AND e.assigned_level = 3 AND e.category_node_id = p_category_node_id)
      );

    RETURN total;
END;
$$;

CREATE OR REPLACE VIEW v_expenses_enriched AS
SELECT
    e.*,
    cn.code AS category_code,
    cn.name_ja AS category_name_ja,
    l1.name_ja AS category_l1_name,
    l2.name_ja AS category_l2_name,
    l3.name_ja AS category_l3_name
FROM expenses e
JOIN category_nodes cn ON cn.id = e.category_node_id
JOIN category_nodes l1 ON l1.id = e.category_l1_id
LEFT JOIN category_nodes l2 ON l2.id = e.category_l2_id
LEFT JOIN category_nodes l3 ON l3.id = e.category_l3_id;
