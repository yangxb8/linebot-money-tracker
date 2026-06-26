# Contract: Category Classification with Memory

**Feature**: 013-tenant-category-memory  
**Modules**: `services/categorize.py`, `services/category_memory.py`, `services/merchant_extract.py`, `services/merchant_normalize.py`, `services/message_handler.py`

## Orchestration entry point

```python
async def classify_expense_with_memory(
    item: dict,
    gemini: GeminiClient,
    *,
    tenant: TenantContext | None = None,
) -> CategoryResultWithProvenance
```

**Returns**:

```python
@dataclass(frozen=True)
class CategoryResultWithProvenance:
    guessed: str           # taxonomy code
    alternatives: tuple[str, ...]
    source: Literal['memory', 'llm']
    merchant_key: str | None
    display_merchant: str | None
```

## Flow

1. `extract_merchant_name(item)` → LLM JSON
2. `normalize_merchant_key(raw)` → key or `None` (generic)
3. If key: `lookup_memory(tenant, key)` 
   - If `weight >= 1.0` and code resolves: return memory result, `source=memory`, **no `classify_expense` call**
4. Else: `classify_expense(item)` → `source=llm`
5. If key: `upsert_memory_llm_seed(tenant, key, guessed)`
6. If key and prior expense qualifies: `apply_silent_confirm(tenant, key)`

## Merchant extract LLM schema

```json
{"merchant_name": "スターバックス"}
```

```json
{"merchant_name": null}
```

**Rules**:
- Extract store/brand/seller, not product name when both present
- Return `null` for generic descriptions (`食費`, `買い物`, etc.)
- Validated server-side; on failure treat as `null` (category LLM only)

**Metering**: `llm_operation_scope('merchant_extract')`

## Category LLM (unchanged output)

```json
{
  "guessed_category_code": "food.grocery",
  "alternatives": ["food.dining", "unknown"]
}
```

On memory hit with `weight >= 1.0`: return `alternatives=()` (empty).

## Expense insert delta

`build_insert_row` / `ExpenseInsertRow` gains:

| Field | Source |
| ----- | ------ |
| category_guess_code | `CategoryResultWithProvenance.guessed` |
| category_source | `CategoryResultWithProvenance.source` |

## Reply-edit hooks

### User correction

After `update_expense_fields(..., category_code=...)` succeeds:

```python
record_user_correction(
    tenant,
    description=expense.description,
    category_code=category_code,
    gemini,
    corrected_by=line_user_id,
)
```

Sets `weight=1.0`, `last_source=user_correction`.

### Category unchanged

Silent confirm **not** triggered from reply-edit directly; handled on next expense log (see research Decision 5).

## Confirmation display (unchanged)

```text
  Category (guess): {L1} > {L2}
  Please confirm or pick another:
  1) {alt 1}
  ...
```

Memory hits use same guess label; alternatives omitted when empty.

## Constants

| Name | Value |
| ---- | ----- |
| `MEMORY_SKIP_WEIGHT_THRESHOLD` | `1.0` |
| `WEIGHT_LLM_SEED` | `0.25` |
| `WEIGHT_SILENT_CONFIRM` | `0.5` |
| `WEIGHT_USER_CORRECTION` | `1.0` |

## Error handling

| Failure | Behavior |
| ------- | -------- |
| Merchant LLM error | Skip memory; category LLM only |
| Memory DB error | Log warning; category LLM only |
| Invalid memory code | Ignore memory; category LLM |
| Generic merchant | No memory read/write |
