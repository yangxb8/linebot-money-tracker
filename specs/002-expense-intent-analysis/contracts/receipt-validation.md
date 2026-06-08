# Contract: Receipt Output Validation

**Feature**: 002-expense-intent-analysis  
**Module**: `services/receipt_validate.py`

## Purpose

Reject untrustworthy parsed receipt items **before** persistence. When validation fails, the bot MUST NOT log expenses (user retries with a clearer photo or text).

## Reject item when

- Description matches payment-slip / card-slip patterns (カード会社, 伝票番号, 承認, `****`, etc.)
- JPY amount &lt; ¥10 or &gt; ¥500,000 per line
- Description too short or empty after cleanup

## Reject entire receipt when

- All items filtered as garbage
- More than 30 line items
- Sum of item amounts differs from parsed 合計 / cash-paid total by more than ¥2 or 5%

## Pipeline interaction

- Applied after `normalize_receipt_items` in the image pipeline
- **No** LLM vision direct item JSON extraction — OCR text → parse → OCR assist only
- **No** total-only fallback when validation fails (clarification 2026-06-08: policy 4B)

## OCR backends

1. PyTesseract (local / Docker)
2. Google Cloud Vision `DOCUMENT_TEXT_DETECTION` via `GOOGLE_VISION_API_KEY`

Document AI is **not** used.
