# Contract: Expense Mutation

**Feature**: 005-expense-reply-edits  
**Module**: `services/expense_repository.py` (extensions)

## New repository methods (predefined only)

```python
def update_expense_fields(
    expense_id: str,
    *,
    description: str | None = None,
    amount: Decimal | None = None,
    currency: str | None = None,
    expense_date: date | None = None,
    category_code: str | None = None,
) -> UpdateResult: ...

def soft_delete_expenses(expense_ids: list[str]) -> MutationResult: ...

def restore_expenses(expense_ids: list[str]) -> MutationResult: ...

def get_expenses_by_ids(expense_ids: list[str]) -> list[ExpenseRow]: ...
```

Category updates MUST recompute `assigned_level`, `category_node_id`, `category_l1/l2/l3_id` via `category_taxonomy.resolve_code` (same as insert path).

## Soft delete semantics

- SET `deleted_at = now()`, `updated_at = now()`
- Row remains in `expenses`
- Excluded from `monthly_expense_total` / `yearly_expense_total` after RPC migration

## Restore semantics

- SET `deleted_at = NULL`, `updated_at = now()`
- Only rows currently soft-deleted are affected

## Atomicity

- Single reply affecting one expense: one UPDATE transaction
- Multi-field update on one expense: single UPDATE with all fields
- `soft_delete_all` after confirm: one UPDATE … WHERE expense_id IN (…) AND deleted_at IS NULL

## Non-blocking

Mutators return `{success, error}`; do not raise to webhook handler under normal DB failures.

## Idempotency interaction

- Soft-delete already deleted row → count as success no-op
- Restore active row → no-op with explanation in summary

## Forbidden

- DELETE FROM expenses (hard delete)
- Dynamic SQL from LLM strings
