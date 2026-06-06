# Research: Supabase Expense Storage

**Feature**: 004-supabase-expense-storage  
**Date**: 2026-06-06 (revised)

## 1. Supabase client access from Python bot

**Decision**: Use official `supabase` Python package with **service role key** on the server (Cloud Run + local webhook). No Supabase Auth for LINE users in v1; tenant key = `line_user_id` text column.

**Rationale**: LINE bot is a trusted backend; users never touch Supabase directly. Service role avoids JWT complexity while RLS still protects against accidental anon-key exposure.

**Alternatives considered**:
- **Postgres driver (asyncpg/psycopg)** — more control but no built-in REST; adds connection pooling burden on Cloud Run
- **Anon key + RLS per LINE user** — requires custom JWT mapping LINE→Supabase; overkill for v1

## 2. LLM / database boundary (critical)

**Decision**: **LLMs NEVER execute or generate SQL.** Gemini returns **validated JSON only** (expense fields, category codes). All database writes and reads go through **application code** calling a fixed set of **predefined operations** in `expense_repository.py` (Supabase table insert / RPC).

**Rationale**: Prevents injection, schema drift, and non-deterministic queries. Matches constitution testability — repository methods are unit-testable with mocks; LLM output is schema-validated before any DB call.

**Pipeline**:

```text
User input → LLM (JSON: expenses / categories) → Pydantic/jsonschema validate
           → map category codes → category_node UUIDs (app lookup)
           → expense_repository.insert_expenses(rows)  # fixed insert only
           → format reply (app string templates)
```

**Alternatives considered**:
- **LLM writes SQL** — rejected (security, unreliability)
- **LLM calls Supabase via tool use** — rejected; same risk as arbitrary queries
- **Natural-language → ORM** — rejected; out of scope

## 3. Predefined database operations

**Decision**: v1 repository exposes only these operations (no ad-hoc query builder):

| Operation | Mechanism | Purpose |
| --------- | --------- | ------- |
| `insert_expenses` | Supabase `.table('expenses').insert(rows)` with conflict handling | Persist detected items |
| `load_category_taxonomy` | `.table('category_nodes').select(...)` once at startup / cache | Map codes → IDs |
| `get_category_by_code` | In-memory map from taxonomy load | Validate LLM category codes |
| `monthly_expense_total` | Postgres RPC `monthly_expense_total(...)` | Analysis tests / future features |
| `yearly_expense_total` | Postgres RPC `yearly_expense_total(...)` | Analysis tests / future features |

Migration SQL defines tables, indexes, unique constraints, and RPC functions. Application never constructs dynamic SQL strings.

**Alternatives considered**:
- **Raw SQL in Python strings** — acceptable only inside repository as constants tied to RPC names; prefer Supabase client insert + RPC for rollups

## 4. Idempotent expense insert

**Decision**: Unique constraint on `(line_user_id, source_message_id, line_item_index)` with insert + conflict detection (Supabase upsert or pre-check + insert).

**Rationale**: Matches FR-014; handles LINE webhook retries; multi-item receipts use `line_item_index` 0..n-1.

**Alternatives considered**:
- **Separate `submissions` table** — cleaner audit trail but extra join; defer unless needed
- **Content-hash dedup** — would block legitimate resends of same receipt text

## 5. Category hierarchy & rollup queries

**Decision**: Adjacency list (`category_nodes.parent_id`) plus **denormalized** `category_l1_id`, `category_l2_id`, `category_l3_id` and `assigned_level` on each expense row. Rollup totals via **fixed RPC functions** in migration SQL.

**Rationale**: Spec requires L3 expenses roll up to ancestors, but L1-only expenses must not appear in L2/L3-only reports. Denormalized columns + parameterized RPCs keep analysis queries predefined.

**Alternatives considered**:
- **ltree extension** — powerful but less portable
- **LLM-generated aggregation queries** — rejected

## 6. LLM categorization output schema

**Decision**: Gemini returns JSON only:

```json
{
  "guessed_category_code": "food.dining.cafe",
  "alternatives": ["food.dining.restaurant", "food.grocery", "unknown"]
}
```

App validates codes against cached taxonomy, resolves UUIDs, computes denormalized L1/L2/L3 columns, then calls `insert_expenses`.

**Alternatives considered**:
- **LLM returns UUIDs** — rejected; LLM should not know DB ids
- **LLM returns Japanese labels only** — ambiguous; codes are canonical

## 7. Timezone for period grouping

**Decision**: Store `expense_date` as `date` interpreted in **JST**; rollup RPCs take `(year, month)` and apply JST boundaries internally.

**Rationale**: Clarification session locked JST for all users.

## 8. Budget table in v1

**Decision**: Create `monthly_budgets` table with FK to `category_nodes` but **no bot CRUD** and no reply impact.

**Rationale**: FR-009 schema placeholder; avoids migration later when budget spec ships.

## 9. Supabase project targeting

**Decision**: Plan and migrations target user project **`https://nyuenufldaqsjybjhawl.supabase.co`**.

**Rationale**: User-provided blank project for linebot-money-tracker; user reconfigured Supabase MCP to this project.

**Verification (MCP 2026-06-06)**: `get_project_url` → `https://nyuenufldaqsjybjhawl.supabase.co`; `list_tables` → empty `public` schema; `list_migrations` → none. Project is blank and ready for expense schema migration.

**MCP server name in Cursor**: `project-0-linebot-money-tracker-supabase` (not `user-supabase`).

## 10. Persistence optional in console mode

**Decision**: If `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` missing in console mode, skip persist with WARNING log; reply unchanged.

**Rationale**: Preserves console-only GEMINI workflow from feature 003 while allowing opt-in DB testing.

## 11. Security — RLS

**Decision**: Enable RLS on `expenses` and `monthly_budgets`; **no** policies for `anon` or `authenticated`. Bot uses service role.

**Rationale**: Prevents data exposure if publishable key leaks.

**Alternatives considered**:
- **RLS disabled** — rejected
