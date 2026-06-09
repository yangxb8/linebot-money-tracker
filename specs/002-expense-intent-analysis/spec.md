# Feature Specification: Expense Intent Analysis

**Feature Branch**: `[002-expense-intent-analysis]`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "Add a new spec to enhance the bot so that it can analyze user input first. And only allow user request to log an expense to be processed (but we will allow more request type in future). User can only send expense via text or a picture, the agent should analyze and return the detected expense in text. If there are multiple expenses (ex. items in a receipt photo), list them separately."

## Clarifications

### Session 2026-06-08

- Q: Image pipeline order — OCR first or Gemini intent first? → A: **OCR and deterministic parse first**; Gemini image intent only when OCR stages find no items. When OCR yields parseable items, **skip** the image intent call (trusted parse).
- Q: Multi-item receipts — logging and categories? → A: **Each line item logged independently** with its **own category** (see 004).
- Q: Per-item amount definition? → A: **Final cash-out share** per item: shelf price + **proportionally allocated tax**, then **proportionally allocated discounts/points used**; ignore points earned. See [receipt-amount-semantics.md](./contracts/receipt-amount-semantics.md).
- Q: Tax allocation? → A: **Proportional by line price**; item amounts must sum roughly to **合計** including tax (LLM assist validates).
- Q: Total-only receipts? → A: Log **one expense** for the final total with merchant name when product lines are unreadable.
- Q: Discount / points used? → A: **Proportional reduction** by tax-inclusive line price toward final cash paid.

### Session 2026-06-08 (iteration 3 — JP receipt format coverage)

- Q: Mixed-tax per-item amounts (Daiso `外`, Shigezo `軽`)? → A: **Tax-inclusive cash-out** per line — shelf price plus proportional tax/discount allocation to match **合計** (same as 1B / [receipt-amount-semantics.md](./contracts/receipt-amount-semantics.md)).
- Q: Quantity lines (Daiso `(@100 x 6個)`, IKEA `2 * 200`)? → A: **One expense per product at line total**; qty may appear in description text only.
- Q: Incomplete parse (IKEA / restaurant / bad OCR)? → A: **Reject and ask retry** — no total-only fallback on validation failure (3A).
- Q: Scope of line items? → A: **Log everything** on the receipt, including bags and low-value lines (≥ ¥1).
- Q: Format coverage priority? → A: **Balanced** — format detectors for IKEA (`商品名`), Daiso (`(@…x…個)`, `外`/`※`), restaurant tabular (`@` / `※`), supermarket `NN*` prefixes; OCR samples as regression tests; supermarket/home-center remain primary.


- Q: Multi-item `取消` alone? → A: **`soft_delete_all`** with YES confirmation (same as 全部取消).
- Q: `全部取消` flow? → A: Two-step **YES** on the bot confirmation message (`是` / YES).
- Q: OCR cloud backend? → A: **Google Cloud Vision** `DOCUMENT_TEXT_DETECTION` with **`GOOGLE_VISION_API_KEY`** (replaces Document AI).
- Q: Low-confidence parse? → A: **Do not log**; ask user to retry photo or send text (no total-only fallback on failed validation).
- Q: Vision item extraction? → A: **Removed** — only OCR text → parse → OCR JSON assist; no direct image→items LLM path.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Detect expense intent from text (Priority: P1)

A user sends a text message describing an expense and the bot analyzes the input before taking action.

**Why this priority**: This is the core value of the feature because accurate intent detection for text expense requests is the primary way users will submit expenses.

**Independent Test**: Send a text message containing an expense description and verify that the bot responds with a parsed expense summary rather than a generic reply.

**Acceptance Scenarios**:

1. **Given** the user sends a text message like "Log lunch expense 120 THB at cafe", **when** the bot receives the text, **then** it identifies the message as an expense logging request and responds with the detected expense details in text.
2. **Given** the user sends a text message that is not an expense request, **when** the bot analyzes the message, **then** it replies that only expense logging requests are currently supported and instructs the user how to submit expense details by text or image.

---

### User Story 2 - Detect expense details from a receipt image (Priority: P2)

A user sends a photo of a receipt or expense document and the bot extracts expense details from the image.

**Why this priority**: Support for image-based expense input is important for convenience and matches the request to accept expense submissions via picture.

**Independent Test**: Send a receipt image and verify that the bot returns a text summary of the expenses detected in the photo.

**Acceptance Scenarios**:

1. **Given** the user uploads a receipt photo containing one expense, **when** the bot processes the image, **then** it returns the detected expense detail in text.
2. **Given** the user uploads a receipt photo containing multiple expense lines, **when** the bot processes the image, **then** it returns each detected expense item separately in the response with amounts reflecting final cash-out (tax and discounts allocated per [receipt-amount-semantics.md](./contracts/receipt-amount-semantics.md)).
3. **Given** OCR extracts parseable line items from a receipt image, **when** the bot processes the image, **then** it proceeds without a separate Gemini image-intent call.

---

### User Story 3 - Reject unsupported request types (Priority: P3)

A user sends a non-expense request and the bot must not process it as an expense.

**Why this priority**: Preventing incorrect processing preserves trust and keeps the feature focused on expense logging only.

**Independent Test**: Send a non-expense message and verify that the bot clearly explains that only expense logging requests are supported at this time.

**Acceptance Scenarios**:

1. **Given** the user asks a general question or sends an unrelated instruction, **when** the bot analyzes the input, **then** it replies with a fixed message that only expense logging requests are supported and suggests sending the expense via text or picture.

---

### Edge Cases

- A receipt image contains text but no clear expense amounts: reply with a request for clearer expense details.
- A text message is ambiguous between expense and non-expense: the bot should clarify that only explicit expense logging is supported.
- A receipt image contains multiple items: the response must list each item separately; each item is categorized independently when persisted (004).
- A receipt shows mixed tax rates or a single 合計: per-item amounts are normalized to **tax-inclusive cash-out** using line tax markers (`外`/`※`/`軽`/`NN*`) when present, else proportional allocation; amounts sum to **合計** within ¥2 tolerance.
- Only 合計 is readable and line items fail validation: **do not log**; ask user to retry (no total-only fallback on failed validation).
- Coupons, 値引, or points **redeemed** at payment reduce per-item amounts proportionally; points **earned** are ignored.
- The input includes different currencies or amounts: preserve the original context in the returned expense text.
- OCR finds items on a non-receipt image: accepted without image-intent call (trusted parse path).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The system MUST determine whether a user message is an expense logging request before processing it. For **images**, Gemini image intent is required only when OCR-based extraction finds **no** parseable items; text intent is unchanged.
- **FR-002**: The system MUST only process requests that are recognized as expense logging requests (or images with trusted OCR parse per FR-001).
- **FR-003**: The system MUST accept expense input submitted as free-form text or as a receipt image.
- **FR-004**: The system MUST return detected expense details in plain text.
- **FR-005**: When multiple expenses are detected in one input, the system MUST list each expense item separately.
- **FR-006**: The system MUST reject non-expense requests with a clear message explaining that only expense logging is supported at this time.
- **FR-007**: The system MUST ask for clarification when the input is ambiguous or does not clearly contain expense data.
- **FR-008**: The system MUST preserve original amounts and currency context when summarizing detected expenses.
- **FR-009**: The system MUST reply with a fixed canned message for unsupported or non-expense requests to avoid unnecessary AI usage.
- **FR-010**: For receipt images, the system MUST run **OCR → deterministic parse → OCR text assist** before Gemini image intent or vision assist.
- **FR-011**: Per-item receipt amounts MUST reflect **final cash-out** per [receipt-amount-semantics.md](./contracts/receipt-amount-semantics.md): tax and discounts/points used allocated proportionally; points earned ignored.
- **FR-012**: When only a receipt total is readable **and line-item validation passes**, a single expense MAY be logged for that total; when validation fails, the system MUST NOT persist and MUST ask the user to retry.
- **FR-013**: The parser MUST support format-specific detectors (balanced coverage): home-center JAN splits, supermarket `NN*` lines, Daiso qty-detail lines, IKEA `商品名` blocks, restaurant tabular rows; see `services/receipt_formats.py` and `samples/*.ocr.txt`.
- **FR-014**: Multi-qty receipt lines MUST log **line totals only** (one expense row per product), not per-unit splits.
- **FR-015**: All product lines including bags and items under ¥10 MUST be logged when parsed (minimum ¥1).

### Key Entities _(include if feature involves data)_

- **Expense Intent**: A user request that intends to log one or more expenses.
- **Expense Item**: A detected expense entry with amount, description, and optionally currency or merchant context.
- **Expense Summary**: The text output returned to the user that describes the detected expense(s).

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Valid expense logging requests submitted as text or image are detected and responded to with parsed expense details in the first reply.
- **SC-002**: When a single receipt contains multiple expenses, each detected item appears separately in the bot response.
- **SC-003**: Non-expense messages are declined with a clear explanation of current support limits.
- **SC-004**: Valid expense submissions do not require additional clarification in more than one follow-up message.

## Assumptions

- The current bot will only process expense logging requests for this feature; other request types are excluded from scope.
- Expense extraction is handled by the agent and returned as text rather than immediately creating a stored transaction record.
- Receipt images will be interpreted as expense data sources; OCR or extraction accuracy may vary but should still produce a best-effort itemized text result.
- Future request types such as budgeting help or analytics are out of scope for this iteration.
