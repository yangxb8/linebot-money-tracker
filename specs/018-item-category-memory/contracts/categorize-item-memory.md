# Contract: Category Classification with Item Memory

**Feature**: 018-item-category-memory  
**Modules**: `services/categorize.py`, `services/category_memory.py`, `services/item_normalize.py`, `services/message_handler.py`, `services/reply_edit.py`

## Entry point

```python
async def classify_expense_with_memory(
    item: dict,
    gemini: GeminiClient,
    *,
    tenant: TenantContext | None = None,
    exclude_source_message_id: str | None = None,
    memory_mode: Literal['merchant', 'item'] = 'merchant',
) -> CategoryResultWithProvenance
```

```python
@dataclass(frozen=True)
class CategoryResultWithProvenance:
    guessed: str
    alternatives: tuple[str, ...]
    source: Literal['memory', 'item_memory', 'llm']
    merchant_key: str | None
    display_merchant: str | None
    item_key: str | None = None
    item_memory_kind: Literal['store_item', 'item_only'] | None = None
```

## message_handler wiring

| Pipeline | `memory_mode` |
| -------- | ------------- |
| Image / receipt parse (`_extract_expense_items_from_image`, OCR receipt path if any) | `item` |
| Text deterministic / assist_parse_text | `merchant` (default) |

## Flow — `memory_mode == 'merchant'` (unchanged 013)

1. Resolve merchant → lookup `category_merchant_memory` → skip if weight ≥ 1.0 (`source=memory`).
2. Else classify → seed merchant +0.25; silent confirm rules unchanged.

## Flow — `memory_mode == 'item'`

1. `resolve_raw_merchant(item)` → `(display, merchant_key)`.
2. `item_key = normalize_item_key(description)`; if None → go to step 5 with no item writes.
3. If `merchant_key`: `lookup_item_memory(tenant, kind='store_item', merchant_key, item_key)`.
4. Else / miss: `lookup_item_memory(tenant, kind='item_only', item_key=item_key)`.
5. If hit and `weight >= 1.0` and `memory_category_is_valid`: return `source=item_memory`, empty alternatives, **no classify LLM**.
6. Else:
   - Optional merchant soft prior: `hint = lookup_memory(tenant, merchant_key).category_code` if merchant_key and row exists (any weight), else None.
   - `classify_expense(item, category_hint=hint)` → `source=llm`.
   - If `merchant_key` and `item_key`: `upsert_item_llm_seed(store_item)` (+0.25). **Never** item_only.
   - Silent confirm on prior store+item identity only (+0.5), excluding current `source_message_id`.

## classify_expense soft prior

```python
async def classify_expense(
    item: dict,
    gemini: GeminiClient,
    *,
    tenant: TenantContext | None = None,
    category_hint: str | None = None,
) -> CategoryResult
```

When `category_hint` set, prompt MUST include the hint as non-binding context for this line item.

## Reply-edit correction

After successful category change on expense row:

```text
IF expense has metadata.store_name (receipt lineage):
  record_item_user_correction(... store_item + item_only ...)
  DO NOT record_user_correction (merchant)
ELSE:
  existing record_user_correction (merchant) path
```

Bulk category change applies the same rule per affected expense.

## Persistence

| Field | Value |
| ----- | ----- |
| category_guess_code | guessed code |
| category_source | `item_memory` \| `memory` \| `llm` |

## Metering / logs

- Memory skip: no `categorize` scope for that line.
- Soft-prior miss: still one `categorize` call; log `item_memory_miss soft_prior={bool}`.
