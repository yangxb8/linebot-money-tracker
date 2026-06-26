# Contract: LLM Vision Receipt Parse with Store Name

**Feature**: 014-receipt-store-name  
**Modules**: `services/ai_assist.py`, `services/receipt_store_name.py`, `services/message_handler.py`

## Prompt delta

Extend `_RECEIPT_IMAGE_PROMPT` to request four top-level fields:

```text
Parse this receipt image into a JSON object with four fields:
- "store_name": the store/merchant/chain name from the receipt header or register
  banner (string or null). NOT a product name. Examples: イオン, セブン-イレブン, マツモトキヨシ.
- "items": array of product/service line items ...
- "total": ...
- "currency": ...
```

Rules added:
- Return `null` for `store_name` when header merchant is unreadable or ambiguous
- Do not put store name in item `description` when product name is also present

## JSON schema

```json
{
  "store_name": "イオン",
  "items": [
    {"description": "牛乳", "amount": 198, "currency": "JPY"},
    {"description": "食パン", "amount": 128, "currency": "JPY"}
  ],
  "total": 1280,
  "currency": "JPY"
}
```

**Schema** (`RECEIPT_IMAGE_PARSE_SCHEMA`):

| Field | Type | Required |
| ----- | ---- | -------- |
| store_name | string \| null | no (optional property) |
| items | array | yes |
| total | number | yes |
| currency | string | yes |

Item schema unchanged: `description`, `amount`, `currency`.

## ReceiptImageParseResult

```python
@dataclass(frozen=True)
class ReceiptImageParseResult:
    items: List[Dict[str, Any]]
    total: Decimal
    currency: str
    store_name: Optional[str] = None
```

## Post-process: propagate_receipt_store_name

```python
def propagate_receipt_store_name(
    items: List[Dict[str, Any]],
    store_name: Optional[str],
) -> List[Dict[str, Any]]:
    ...
```

**Behavior**:

| Condition | Result |
| --------- | ------ |
| `store_name` non-empty after strip | All items get same `store_name` |
| `store_name` null/empty | All items: key absent or null |
| Items have conflicting non-null store_name ≠ receipt-level | All items: null |

Called in `_extract_expense_items_from_image` after `_prepare_llm_receipt_items`.

## Metering

Unchanged: vision call under existing `assist_parse_image` path (no new LLM scope).

## Error handling

| Failure | Behavior |
| ------- | -------- |
| Invalid JSON | Return `None` (existing) |
| Schema fail on items/total | Return `None` (existing) |
| Invalid/missing store_name | Parse succeeds; `store_name=None`; items still logged |
| Empty items | Return `None` (existing) |

## Out of scope (v1)

- OCR `assist_parse_ocr` — no store_name
- Text `assist_parse_text` — no store_name
