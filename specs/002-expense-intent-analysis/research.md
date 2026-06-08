# Research: Image Expense Extraction & Cost-Effective Parsing

**Feature**: Expense Intent Analysis
**Date**: 2026-06-02

Purpose: evaluate approaches to extract expense line items from receipt images while minimizing AI usage and cost. Recommend a practical, testable hybrid approach for the MVP.

1. Problem statement

- Accept receipt images (photos) and return one or more detected expense items as plain text.
- Preserve amounts, currencies, and merchant/description context.
- Minimize AI calls and cost; prefer deterministic parsing where possible.

2. Candidate approaches

A. Pure AI image-to-structured extraction

- Send the image directly to an LLM/vision+LLM pipeline (e.g., Gemini multimodal) and request structured JSON.
- Pros: high flexibility, can handle messy layouts and handwriting.
- Cons: high per-call cost; less deterministic; higher latency.

B. OCR-first + deterministic parsing (recommended primary path)

- Run OCR locally (pytesseract) or a cloud OCR (Google Document AI) to get raw text lines.
- Apply deterministic heuristics and regexes to detect amounts, currencies, and probable item lines.
- If parsing succeeds with high confidence, return parsed results without any AI call.
- Pros: low cost, deterministic, fast. Works for most printed receipts.
- Cons: less robust on very noisy images or handwriting.

C. OCR-first + AI-assisted disambiguation (recommended hybrid) — **implemented**

- Run OCR as in B. If deterministic parser yields ambiguous or low-confidence output (e.g., multiple candidate amounts, no clear lines), call the AI with a small, focused prompt that asks for structured extraction from the OCR text only.
- Limit AI call scope: pass OCR text, not raw image, and request compact JSON with strict schema. Use the smallest capable model or low-latency variant.
- **Gemini image intent** runs only when OCR stages find **no** items; trusted OCR parse skips intent (2026-06-08 clarification).
- **Vision assist** runs only after image intent confirms a receipt.
- Pros: much lower AI cost than A; better robustness than B alone.
- Cons: still incurs AI cost for edge cases; OCR false positives on non-receipt images are accepted for cost savings.

D. Document AI + lightweight parsing

- Use Google Document AI OCR (higher accuracy) as the cloud fallback OCR source, then apply deterministic parsing or hybrid AI assist when needed.
- Tradeoff: Document AI costs vs. local OCR accuracy; may still be cheaper than full LLM vision calls for each image.

3. Cost-reduction tactics (practical)

- Prefer local OCR (`pytesseract`) for initial extraction; add `pytesseract` to `requirements.txt` only for optional lightweight deployments.
- Use deterministic parsing rules for common receipt formats (regex for currency/amount, line heuristics for description). If confident, return results without contacting Gemini.
- For images that fail deterministic parsing, send only OCR text to the AI (avoid sending the image). This reduces model processing needs and tokens.
- Use compact structured prompts that ask for minimal JSON output (no extra text). This reduces token usage and parsing overhead.
- Cache results for repeated identical images or repeated OCR outputs to avoid duplicate AI calls.
- Limit the model call: set a small `max_output_tokens`, use a small model if available, and restrict temperature to 0 for deterministic outputs.
- Batch parsing: if the bot receives multiple images quickly from the same user, consider batching OCR outputs into a single AI call to amortize cost (only for advanced flows).

4. Implementation recommendations (MVP)

Phase 0 (research & prototype)

- Implement `services/ocr.py` that exposes `extract_text_from_image(image_bytes) -> List[str]` with two backends:
  - Local: `pytesseract` via `Pillow` image processing
  - Cloud: optional Google Document AI client (config-driven)
- Implement `services/receipt_parser.py` that applies deterministic parsing:
  - Normalize OCR lines (trim, unify separators)
  - Regex search for currency symbols and numbers (handle common formats: 1,234.56; 1.234,56; 1234)
  - Identify candidate item lines via heuristics (line length, presence of amount tokens)
  - Output `List[ExpenseItem]` where `ExpenseItem = {description, amount, currency, raw_line}` and a `confidence` score
- Develop a thin AI orchestrator `services/ai_assist.py` that:
  - Accepts OCR lines and parser output
  - If parser indicates low confidence or ambiguous results, call `GeminiClient.generate_reply()` with a concise prompt that returns JSON in a strict schema
  - Validate the JSON against the expected schema and fallback to requesting clarification if invalid

Phase 1 (integration & tests)

- Wire parsing flow into `main.py` webhook handler for image events
- Add unit tests for `receipt_parser` covering different OCR outputs and formats
- Add integration tests mocking `GeminiClient` to assert AI assist path is only invoked for ambiguous input

5. Prompt design (cost-conscious)

- Input to AI: only OCR text (not the image) plus minimal instructions and schema
- Example prompt (short):

"Parse the following OCR text from a receipt into JSON array of items. Each item must include: description, amount (numeric), currency (3-letter or symbol). Return only valid JSON array. OCR_TEXT:\n<lines>"

- Enforce schema in prompt and use `temperature=0`, `max_output_tokens=200`.

6. Acceptance criteria for research

- Deterministic parser correctly extracts single-line receipts with >=95% precision on a small sample corpus.
- Hybrid flow calls AI for <20% of images in an initial test set.
- AI responses conform to the JSON schema without additional text in >=95% of assisted cases.

7. Receipt amount normalization (2026-06-08)

- Module: `services/receipt_normalize.py`
- Per-item amounts = shelf price + proportional tax + proportional discount/points-used adjustment toward final cash paid.
- Ignore points earned; sum of items ≈ 合計 within ¥2.
- Total-only fallback: one line expense when only 合計 is parseable.
- Contract: [contracts/receipt-amount-semantics.md](./contracts/receipt-amount-semantics.md)

8. Next steps & tasks

- Implement `services/ocr.py` and `services/receipt_parser.py` prototypes.
- Create a small corpus of sample receipts (images or OCR output) for unit testing.
- Add tests that assert AI is not invoked for clearly-parseable receipts.
- Document deployment considerations for optional cloud OCR vs local OCR.

Appendix: Libraries & tools to consider

- `pytesseract` + `Pillow` (local OCR)
- `google-cloud-documentai` (cloud OCR fallback)
- `regex` / `decimal` for robust number parsing
- `jsonschema` for validating AI outputs

Recommended short canned reply for unsupported inputs (to put in `main.py`):

"Sorry—I only accept expense submissions right now. Please send a receipt image or a text message like: `Lunch 120 THB at Cafe`"
