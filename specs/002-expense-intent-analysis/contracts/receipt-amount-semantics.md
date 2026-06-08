# Contract: Receipt Amount Semantics

**Feature**: 002-expense-intent-analysis (cross-ref 004-supabase-expense-storage)  
**Modules**: `services/receipt_parser.py`, `services/receipt_normalize.py`, `services/ai_assist.py`

## Purpose

Define how per-line expense amounts are derived from receipt images so logged totals reflect **actual cash out**, not shelf subtotals alone.

## Multi-item logging

- Each detected product/service line MUST become a **separate expense item** in the bot reply.
- Each item MUST receive its **own category classification** at persist time (see [004 categorization contract](../../004-supabase-expense-storage/contracts/categorization-reply.md)).
- Summary lines (小計, 合計, 税, 支払, お釣り) MUST NOT be logged as separate items.

## Amount definition

Each item `amount` is the **final cash-out share** for that line:

1. Start from the **shelf / tag line price** on the receipt.
2. **Allocate tax** proportionally by line price so item amounts include tax and sum to the receipt total including tax (合計).
3. **Allocate discounts and points used** proportionally by (tax-inclusive) line price so item amounts sum to **final cash paid** (支払 / 合計 when no separate payment line).
4. **Ignore points earned** (ポイント付与 / 獲得) — they do not change logged amounts.

### Allocation rules (clarified 2026-06-08)

| Adjustment | Rule |
| ---------- | ---- |
| Tax (外税 / 内税 / 消費税) | **Proportional by pre-tax line price** across product lines |
| Coupons, 値引, 割引, points **redeemed** at payment | **Proportional by tax-inclusive line price** |
| Points **earned** | **Ignored** |
| Rounding | Distribute remainder (≤ ¥1 per item) to the largest line so the sum matches cash paid within **¥2** tolerance |

### Validation

- After normalization (deterministic or LLM assist), the sum of item amounts MUST be within **¥2** of the receipt **合計** or payment-line total.
- LLM assist prompts MUST instruct the model to verify this constraint.
- Mismatches beyond tolerance are logged at WARNING; deterministic normalization adjusts when receipt totals are parseable.

## Total-only fallback

**Deprecated for image pipeline (2026-06-08).** When validation fails, do not log a total-only expense — return a parse-error reply instead.

## Image processing pipeline

```text
OCR (Tesseract → Cloud Vision DOCUMENT_TEXT_DETECTION)
  → deterministic parse → normalize → validate
  → if invalid & OCR text remains → OCR text assist (JSON) → normalize → validate
  → if still invalid & OCR was empty → Gemini image intent (receipt check only)
  → if not receipt → canned unsupported
  → if receipt but still invalid → parse-error reply (no DB writes)
```

See also [receipt-validation.md](./receipt-validation.md).

**Intent (FR-001)**: Gemini image classification is required only when OCR stages find **no** parseable items. High-confidence OCR parse is trusted without an extra intent call (cost reduction).

## LLM assist schema

Same as [llm-db-boundary](../../004-supabase-expense-storage/contracts/llm-db-boundary.md) expense detection output:

```json
[{"description": "string", "amount": 123.45, "currency": "JPY"}]
```

Prompt MUST include:

- Exclude subtotal / tax / total / payment / change lines from the item array.
- Per-item amounts are tax-inclusive and reflect proportional discounts/points **used**.
- Ignore points earned.
- Item amounts should sum to roughly 合計 / cash paid.
