# Contract: Expense Persistence

**Feature**: 004-supabase-expense-storage  
**Module**: `services/expense_repository.py`

See also: [llm-db-boundary.md](./llm-db-boundary.md) — LLM outputs JSON only; this module performs all writes.

## Trigger

After successful expense detection (text or image), JSON validation, and categorization mapping, before returning reply to user.

## Repository API (predefined operations only)

```python
def insert_expenses(rows: list[ExpenseInsertRow]) -> PersistResult: ...

def load_category_taxonomy() -> dict[str, CategoryNode]: ...

def monthly_expense_total(
    line_user_id: str, year: int, month: int,
    category_node_id: str, currency: str,
) -> Decimal: ...  # calls RPC

def yearly_expense_total(
    line_user_id: str, year: int,
    category_node_id: str, currency: str,
) -> Decimal: ...  # calls RPC
```

No other public DB methods in v1.

## Input to `insert_expenses`

Built by application code from validated LLM JSON + taxonomy lookup (not by LLM directly):

```python
ExpenseInsertRow:
  line_user_id: str
  source_message_id: str
  line_item_index: int
  description: str
  amount: Decimal
  currency: str          # 3-letter ISO
  expense_date: date    # JST
  category_node_id: uuid
  assigned_level: int   # 1..3
  category_l1_id: uuid
  category_l2_id: uuid | None
  category_l3_id: uuid | None
```

## Database mechanism

Fixed insert into `public.expenses` via Supabase client:

```python
client.table("expenses").insert([row_dict, ...]).execute()
```

Idempotency: unique index on `(line_user_id, source_message_id, line_item_index)`. On conflict, count as `skipped` (implementation may use upsert with `ignoreDuplicates` or catch duplicate error).

**MUST NOT** use LLM-generated SQL or dynamic table/column names.

## Behavior

| Condition | Action |
| --------- | ------ |
| Supabase configured | `insert_expenses` for all validated rows |
| Supabase not configured (console) | Log warning; return empty result |
| Supabase error | Log exception; return `{error: ...}`; **do not raise** |
| Zero detected items | No database call |
| Invalid category code after mapping | Use `unknown` node before insert |

## Output

```python
@dataclass
class PersistResult:
    inserted: int
    skipped: int
    error: Optional[str]
```

## Non-blocking guarantee (FR-011)

`insert_expenses` MUST NOT raise to `message_handler` under normal Supabase failures.

## Environment

- `SUPABASE_URL=https://nyuenufldaqsjybjhawl.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY=<secret>`

Optional in console mode.
