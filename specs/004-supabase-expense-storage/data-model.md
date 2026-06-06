# Data Model: Supabase Expense Storage

**Feature**: 004-supabase-expense-storage

## ERD (conceptual)

```text
category_nodes (seed, shared)
    │
    ├──< expenses >── line_user_id (tenant)
    │
    └──< monthly_budgets >── line_user_id (tenant, placeholder)
```

## Entity: category_nodes

Predefined Japanese-household taxonomy. Seeded via migration; not user-editable in v1.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | gen_random_uuid() |
| code | text UNIQUE NOT NULL | Stable slug e.g. `food.dining.cafe` |
| name_ja | text NOT NULL | Display label e.g. `カフェ` |
| level | smallint NOT NULL | 1, 2, or 3 |
| parent_id | uuid FK → category_nodes | NULL for L1 |
| sort_order | int | UI / prompt ordering |

**Constraints**:
- `level = 1` ⇒ `parent_id IS NULL`
- `level > 1` ⇒ `parent_id IS NOT NULL`
- Max depth 3 enforced by seed + check trigger optional

**Special row**: `code = 'unknown'`, `name_ja = '不明'`, `level = 1`, no children.

## Entity: expenses

One row per detected expense line item.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | |
| line_user_id | text NOT NULL | LINE `userId` or `local-dev-user` |
| source_message_id | text NOT NULL | LINE message id or console UUID |
| line_item_index | int NOT NULL DEFAULT 0 | 0..n-1 within same message |
| description | text NOT NULL | |
| amount | numeric(14,2) NOT NULL | |
| currency | char(3) NOT NULL | ISO 4217 |
| expense_date | date NOT NULL | JST calendar date |
| category_node_id | uuid FK NOT NULL | Deepest assigned node |
| assigned_level | smallint NOT NULL | 1, 2, or 3 |
| category_l1_id | uuid FK NOT NULL | Denormalized ancestor |
| category_l2_id | uuid FK NULL | Set when assigned_level ≥ 2 |
| category_l3_id | uuid FK NULL | Set when assigned_level = 3 |
| created_at | timestamptz NOT NULL DEFAULT now() | |

**Unique**: `(line_user_id, source_message_id, line_item_index)`

**Indexes**:
- `(line_user_id, expense_date)`
- `(line_user_id, category_l1_id, expense_date)`
- `(line_user_id, source_message_id)`

## Entity: monthly_budgets (placeholder)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | |
| line_user_id | text NOT NULL | |
| category_node_id | uuid FK NOT NULL | Budget applies to this node |
| budget_month | date NOT NULL | First day of month in JST e.g. `2026-06-01` |
| amount | numeric(14,2) NOT NULL | |
| currency | char(3) NOT NULL | |
| created_at | timestamptz NOT NULL DEFAULT now() | |

**Unique**: `(line_user_id, category_node_id, budget_month, currency)`

No rows required in v1.

## Rollup semantics

| assigned_level | category_node_id | In L1 total for ancestor? | In L2 total for child? | In L3 total for leaf? |
| -------------- | ---------------- | ------------------------- | ---------------------- | --------------------- |
| 1 | L1 node A | Yes (exact A only) | No | No |
| 2 | L2 node B | Yes (via l1) | Yes (exact B) | No |
| 3 | L3 node C | Yes (via l1) | Yes (via l2) | Yes (exact C) |

**Monthly total for category node N** (JST month M):

```sql
-- Pseudocode: filter expense_date in month M (JST)
-- Include row if:
--   (assigned_level = N.level AND category_node_id = N.id)
--   OR (assigned_level > N.level AND category_l{N.level}_id = N.id)
```

## Views (migration)

### v_expenses_enriched

Joins expenses → category_nodes for display paths (`食費 > 外食 > カフェ`).

### v_monthly_expense_totals

Groups by `line_user_id`, `date_trunc('month', expense_date)`, `category_node_id` (rollup target), `currency`, `sum(amount)`.

Implemented as SQL function `monthly_expense_total(p_user_id, p_year, p_month, p_category_id)` for parameterized queries.

### v_yearly_expense_totals

Same pattern grouped by calendar year (JST).

## Seeded taxonomy (summary)

See `data/category_taxonomy_ja.yaml` at implement time. Top-level L1 nodes (Japanese family):

| code | name_ja |
| ---- | ------- |
| food | 食費 |
| housing | 住居 |
| utilities | 光熱・通信 |
| transport | 交通 |
| healthcare | 医療・健康 |
| education | 教育・子ども |
| clothing | 被服・美容 |
| leisure | 娛楽・交際 |
| personal | 嗜好品 |
| finance | 金融・保険 |
| unknown | 不明 |

Each L1 has 2–4 L2 children; selected L2 nodes have L3 children (e.g. `food.dining.cafe`).

## MessageContext (application, not persisted)

| Field | Source |
| ----- | ------ |
| line_user_id | LINE `event.source.user_id` or `local-dev-user` |
| source_message_id | LINE `event.message.id` or `uuid4()` per console run |

## State transitions

```text
[Detect expense items]
  → [LLM categorize each item]
  → [INSERT expenses ON CONFLICT DO NOTHING]
  → [Format reply with guess + alternatives]
  → (optional) [User picks alternative in chat → ack only, no UPDATE in v1]
```

Storage failure branch: skip INSERT, log error, still format reply.

## Relationships to existing code

- `parse_text_for_expenses` / image pipeline → list of `{description, amount, currency}` (+ optional date)
- `categorize.classify_expense(item, taxonomy)` → JSON `{guessed_category_code, alternatives}` — **no DB access**
- `category_taxonomy.resolve(code)` → `CategoryNode` with UUIDs and ancestor chain
- `expense_repository.build_insert_row(...)` → app-computed denormalized columns
- `expense_repository.insert_expenses(rows)` → fixed Supabase insert
- `expense_repository.monthly_expense_total(...)` → fixed RPC (tests / future analysis)
