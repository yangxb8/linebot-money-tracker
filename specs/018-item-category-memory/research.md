# Research: Item-Level Category Memory for Receipts

**Feature**: 018-item-category-memory

## Decision 1: Separate `category_item_memory` table (not overload merchant table)

**Decision**: Add `category_item_memory` with `memory_kind` ∈ {`store_item`, `item_only`}, `item_key`, and nullable `merchant_key` (required when `store_item`). Keep `category_merchant_memory` for text-path 013 behavior.

**Rationale**: Different uniqueness and write policies (item-only correction-only; store+item accepts LLM/silent/backfill). Overloading merchant rows would force sentinel keys and risk accidental hard-skip bugs.

**Alternatives considered**:
- **Widen `category_merchant_memory`** with nullable `item_key` — rejected; uniqueness with NULL and dual skip semantics become error-prone.
- **Item-key only (drop merchant in key)** — rejected by clarify (prefer store+item then item-only).

## Decision 2: Receipt path detection via `memory_mode`

**Decision**: `classify_expense_with_memory(..., memory_mode: Literal['merchant','item']='merchant')`. Image/receipt pipeline in `message_handler` passes `memory_mode='item'` for **all** lines from that parse (including single-line photos). Text / assist-text paths keep default `merchant`.

**Rationale**: Spec scopes item memory to receipt/image parses, not “has store_name”. Multi-item text remains merchant-only (FR-002).

**Alternatives considered**:
- Infer from `store_name` alone — fails for receipt photos with missing store; incorrectly switches some text rows that gained store_name later.
- Always item mode when description “looks like product” — too heuristic.

## Decision 3: Lookup / skip order on `memory_mode='item'`

**Decision**:

1. Resolve `merchant_key` via existing `resolve_raw_merchant` (store_name preferred).
2. Derive `item_key` via `normalize_item_key(description)`; if None → classify with optional soft prior; no item write.
3. Lookup `store_item` for `(merchant_key, item_key)` if merchant_key present.
4. Else lookup `item_only` for `item_key`.
5. If hit and `weight ≥ 1.0` and code valid → return `source='item_memory'`, skip category LLM.
6. Else `classify_expense(..., category_hint=merchant_memory_code or None)` then upsert **store_item only** (+0.25) when merchant_key + item_key exist.
7. Silent confirm strengthens **store_item only** (+0.5) using prior expense match on same store+item identity — never item_only.

**Rationale**: Matches clarify A/C/B/A decisions.

## Decision 4: Soft prior via classify prompt hint

**Decision**: Extend `classify_expense` with optional `category_hint: str | None`. When present, prompt includes: “Merchant often categorized as `{code}` (`{name}`); choose the best code **for this line item**, which may differ.” Do not pre-assign.

**Rationale**: Accuracy-first cold start without hard-skip (clarify B).

**Alternatives considered**: Ignore merchant memory on receipts — more LLM freedom but loses specialty-store signal; hard fallback for “ambiguous” lines — reintroduces bugs.

## Decision 5: Item-only writes only on explicit correction

**Decision**: `record_item_user_correction` upserts both `store_item` (if merchant known) and `item_only` at weight 1.0. LLM seed / silent / backfill never touch `item_only`.

**Rationale**: Clarify C — avoid cross-store thrash from LLM noise.

## Decision 6: Reply-edit isolation from merchant memory

**Decision**: On category reply-edit for expenses logged with `category_source` in {`item_memory`,`llm`} **and** `metadata.store_name` present (receipt lineage), call item correction APIs only — **do not** call `record_user_correction` (merchant). Text-path / merchant-sourced expenses keep today’s merchant correction.

**Rationale**: FR-011 — one toilet-paper correction must not rewrite 島忠 → 日用品 globally.

**Alternatives considered**: Always update both — rejected by clarify 5A/FR-011.

## Decision 7: Provenance value `item_memory`

**Decision**: Expand `expenses.category_source` CHECK to allow `item_memory` | `memory` | `llm`. Item-path hits use `item_memory`; text merchant hits remain `memory`.

**Rationale**: SC-002 skip metering and analytics without overloading `memory`.

## Decision 8: Deterministic `item_key` normalization (v1)

**Decision**: `normalize_item_key(description) -> str | None`:

1. Start from `clean_receipt_description`.
2. NFKC; lowercase ASCII letters; compress whitespace.
3. Strip trailing size/pack/model tokens: `\b[Ww]\d+\b`, single trailing letter tokens length 1, `ロール*`, qty like `\d+[個本枚入袋組]`, parenthetical pack info.
4. Strip leading shelf/dept numeric codes already mostly removed by clean.
5. Remove punctuation except CJK and alphanumerics; produce compact key (whitespace → `_` for ASCII mix; CJK kept concatenated after space strip).
6. Generic denylist (商品, 不明, 税, 小計, expense/item, length < 2) → None.

**Rationale**: Spec assumes deterministic rules; fuzzy match out of scope. Aggressive enough to map `陶器プランターW2 A` ≈ `陶器プランター`.

**Alternatives considered**: Embeddings — out of scope; keep raw cleaned description as key — poorer rematch.

## Decision 9: Backfill eligibility

**Decision**: Script `scripts/backfill_category_item_memory.py` scans non-deleted expenses where `metadata ? 'store_name'` (receipt lineage from 014), derives merchant_key + item_key, upserts `store_item` with `last_source=backfill`, weight capped at 1.0, last expense wins per key. Never writes `item_only`.

**Rationale**: Clarify B; FR-018–020.

## Decision 10: Security / RLS

**Decision**: New table follows `category_merchant_memory`: service-role access from bot; **no web anon policies in v1**. Document same intentional pattern as 013 (table not exposed via user JWT flows). Do not enable RLS without companion deny/allow policies for anon.

**Rationale**: Matches existing memory table ops model; web UI out of scope.

## Decision 11: Complexity tracking

No constitution violations. Added modules are justified by separate write/lookup semantics vs merchant memory.
