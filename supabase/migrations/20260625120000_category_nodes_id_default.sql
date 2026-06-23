-- category_nodes.id was created without a default; web POST /api/categories
-- inserts without id and failed with NOT NULL violation.

ALTER TABLE category_nodes
    ALTER COLUMN id SET DEFAULT gen_random_uuid();
