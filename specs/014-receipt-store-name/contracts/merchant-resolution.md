# Contract: Merchant Resolution with Store Name

**Feature**: 014-receipt-store-name  
**Modules**: `services/merchant_resolve.py`, `services/categorize.py`, `services/category_memory.py`, `services/reply_edit.py`

## Entry point

```python
async def resolve_raw_merchant(
    item: dict,
    gemini: GeminiClient,
) -> tuple[Optional[str], Optional[str]]:
    """Return (raw_merchant, merchant_key). Either may be None."""
```

## Resolution order

1. **store_name path** (FR-005)
   - `raw = strip_branch_suffix(str(item.get('store_name', '')).strip())`
   - If empty or `is_generic_merchant_text(raw)`: goto step 2
   - `key = normalize_merchant_key(raw)`
   - If `key`: return `(raw, key)` — **no merchant_extract LLM**

2. **Description fallback** (013)
   - `raw = await extract_merchant_name(description, gemini, amount=..., currency=...)`
   - `key = normalize_merchant_key(raw)`
   - Return `(raw, key)`

## classify_expense_with_memory integration

Replace direct `extract_merchant_name` call with:

```python
raw_merchant, merchant_key = await resolve_raw_merchant(item, gemini)
```

Downstream memory lookup, category LLM, silent confirm unchanged from 013 contract.

## Reply-edit integration

```python
async def record_user_correction_from_description(
    tenant,
    *,
    description: str,
    category_code: str,
    gemini: GeminiClient,
    store_name: Optional[str] = None,  # NEW
    corrected_by: Optional[str] = None,
) -> None:
```

When `store_name` provided:
- Build synthetic `item = {'store_name': store_name, 'description': description}`
- Use `resolve_raw_merchant` (or inline same rules without extra LLM when store normalizes)

`reply_edit._record_category_memory_correction` loads expense metadata and passes `store_name`.

## Backfill helper

```python
def merchant_key_from_expense_row(row: dict) -> Optional[str]:
    meta = row.get('metadata') or {}
    store = meta.get('store_name')
    if store and str(store).strip():
        key = normalize_merchant_key(strip_branch_suffix(str(store).strip()))
        if key:
            return key
    return heuristic_merchant_from_description(str(row.get('description', '')))
```

## Constants (unchanged from 013)

| Name | Value |
| ---- | ----- |
| `MEMORY_SKIP_WEIGHT_THRESHOLD` | `1.0` |

## Error handling

| Failure | Behavior |
| ------- | -------- |
| store_name present but normalize null | Fall back to description merchant LLM |
| merchant LLM error | `merchant_key=None`; category LLM only (013) |
| Generic store_name | Treated as absent; description path |

## Observability

Log at INFO when store_name path used vs description fallback:

```text
merchant_resolve: source=store_name key=aeon raw=イオン
merchant_resolve: source=description key=lawson (store_name normalize failed)
```
