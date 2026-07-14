# Contract: Item Key Normalization

**Feature**: 018-item-category-memory  
**Module**: `services/item_normalize.py`

## API

```python
def normalize_item_key(description: str | None) -> str | None:
    """Return stable item_key or None when generic / empty."""
```

## Pipeline

1. `clean_receipt_description(description)` (existing).
2. Unicode NFKC.
3. Strip trailing / embedded noise tokens (regex, iterative):
   - Model/size: `(?i)\bW\d+\b`, trailing single Latin letter as separate token
   - Pack/qty: `\d+\s*[個本枚入袋組缶卷卷ケースパック]?`, `ロール+`, `@\s*\d+`
   - Leftover register crumbs if any: `P\d{13}`, `内\d+`
4. Remove punctuation except letters/digits/CJK; collapse whitespace.
5. Build key:
   - If any ASCII letter/digit remains mixed with CJK: lowercase ASCII, join tokens with `_`, keep CJK contiguous.
   - Pure CJK: remove spaces, keep character sequence.
6. Reject if:
   - empty / length < 2
   - in generic denylist: `商品`, `不明`, `税`, `合計`, `小計`, `expense`, `item`, `product`, `misc`, …

## Examples

| Input (cleaned) | item_key |
| --------------- | -------- |
| `園芸 陶器プランターW2 A` | `園芸陶器プランター` or `陶器プランター`* |
| `シャワートイレ用パルプ ロールダブル` | `シャワートイレ用パルプ` |
| `牛乳` | `牛乳` |
| `商品` | `None` |

\* Prefer stripping leading department-only tokens only when a longer product token remains; v1 MAY keep `園芸` prefix if splitting is ambiguous — document chosen regex in implementation tests.

## Non-goals

- Fuzzy / edit-distance matching
- Synonym dictionary (トイレットペーパー ↔ ティッシュ) in v1
- Merchant extraction (handled separately)
