# Contract: Supabase Schema

**Feature**: 004-supabase-expense-storage  
**Target project**: `https://nyuenufldaqsjybjhawl.supabase.co`

## Migration file

`supabase/migrations/20260606120000_expense_schema.sql`

## Tables created

| Table | Purpose | RLS |
| ----- | ------- | --- |
| `category_nodes` | Seeded JP-family taxonomy | Optional (read-only seed) |
| `expenses` | User expense records | **Enabled**, no anon/authenticated policies |
| `monthly_budgets` | Future budget limits | **Enabled**, no anon/authenticated policies |

## Idempotency constraint

```sql
UNIQUE (line_user_id, source_message_id, line_item_index)
```

Insert pattern:

```sql
INSERT INTO expenses (...)
ON CONFLICT (line_user_id, source_message_id, line_item_index) DO NOTHING
RETURNING id;
```

## Rollup functions

| Function | Parameters | Returns | Called by |
| -------- | ---------- | ------- | --------- |
| `monthly_expense_total` | `p_line_user_id`, `p_year`, `p_month`, `p_category_node_id`, `p_currency` | `numeric` | `expense_repository` RPC only |
| `yearly_expense_total` | `p_line_user_id`, `p_year`, `p_category_node_id`, `p_currency` | `numeric` | `expense_repository` RPC only |

Both defined in migration SQL. **Not callable by LLM.** Application passes typed parameters only.

## Insert path

Application uses Supabase client table insert — **not** LLM-generated SQL:

```python
client.table("expenses").insert([...]).execute()
```

See [llm-db-boundary.md](./llm-db-boundary.md).

## Seed data

Migration inserts all rows from taxonomy seed (see `data/category_taxonomy_ja.yaml`). Must include `unknown` node.

## Apply methods

1. Supabase MCP `apply_migration` (after linking correct project)
2. Supabase Dashboard → SQL Editor → paste migration
3. Supabase CLI `supabase db push` (if CLI linked to project)

## MCP mismatch warning

If `list_tables` shows `monitored_pages`, `check_runs`, etc., MCP is pointed at the **wrong** project. Do not apply expense migrations there.
