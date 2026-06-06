# Contract: LLM ↔ Database Boundary

**Feature**: 004-supabase-expense-storage

## Rule

**The LLM MUST NOT generate or execute SQL queries.** It produces **structured JSON** only. The Python application validates that JSON and performs database operations through **named, predefined repository methods**.

## LLM responsibilities (JSON output only)

| Stage | Module | JSON schema (validated) |
| ----- | ------ | ------------------------ |
| Expense detection (existing) | `ai_assist`, `receipt_parser` | `[{description, amount, currency}]` |
| Category assignment (new) | `categorize` | `{guessed_category_code, alternatives[]}` max 3 |

Validation: `jsonschema` / existing validators before any DB access.

## Application responsibilities (no LLM)

| Step | Module | Action |
| ---- | ------ | ------ |
| Resolve category code → node | `category_taxonomy` | Lookup in cached `category_nodes` map |
| Compute denormalized IDs | `expense_repository` | Set `category_l1/l2/l3_id`, `assigned_level` from node |
| Insert rows | `expense_repository.insert_expenses` | Fixed Supabase insert into `expenses` |
| Format user reply | `message_handler` | String templates from resolved Japanese paths |
| Analysis totals (tests/future) | `expense_repository` | Call RPC `monthly_expense_total` / `yearly_expense_total` |

## Forbidden patterns

- Passing SQL strings from Gemini to Supabase
- Gemini tool/function calling that hits the database
- Dynamic `f"SELECT ... {user_input}"` query construction
- Letting LLM choose table or column names at runtime

## Allowed Supabase access patterns

```python
# Insert — predefined columns only
client.table("expenses").insert([{...}]).execute()

# Taxonomy load — fixed select
client.table("category_nodes").select("id,code,level,parent_id,name_ja").execute()

# Rollup — fixed RPC name + typed params
client.rpc("monthly_expense_total", {
    "p_line_user_id": user_id,
    "p_year": 2026,
    "p_month": 6,
    "p_category_node_id": category_id,
    "p_currency": "JPY",
}).execute()
```

## Error handling

| Failure | Behavior |
| ------- | -------- |
| Invalid LLM JSON | Log; use `unknown` category or skip item; still reply if possible |
| Unknown category code | Map to `unknown` node |
| Insert failure | Log; do not block user reply (FR-011) |
