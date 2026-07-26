# Research: Wish List

**Feature**: 020-wish-list  
**Date**: 2026-07-26

## Decision 1: First-class `wish_list_items` table + expense FK

**Decision**: Persist wish list rows in a new tenant-scoped `wish_list_items` table. On execute, set `expenses.wish_list_item_id` (nullable FK), mirroring `periodic_schedule_id`. Status on the wish item: `active` | `executed`. Store `executed_expense_id` for the executed filter link.

**Rationale**: Spec requires active vs executed lifecycle, priority order, and expense-card tagging. A FK is queryable and consistent with periodic origin tagging. Overloading `expenses.metadata` or `category_source` would blur unrelated concerns.

**Alternatives considered**:
- Metadata-only flag on expenses without a wish table — rejected; cannot support active priority list or bot add before purchase.
- Soft-delete-only (no status) — rejected; executed items must remain filterable without looking like active priorities.

---

## Decision 2: Manual priority via `sort_order`, sorts are view modes

**Decision**: Persist integer `sort_order` per active item (dense or gap-friendly; reorder API rewrites the active set). Default UI uses `sort_order ASC`. “Sort by created time” and “sort by price” are **presentation modes** (client or query `ORDER BY`) and do not rewrite `sort_order` unless the user explicitly reorders in priority mode.

**Rationale**: Spec requires persistent manual priority plus automatic sorts. Mutating priority when switching sort modes would destroy user ordering.

**Alternatives considered**:
- Separate priority table — rejected; unnecessary for single ordered list per ledger.
- Always persist last-used sort as canonical order — rejected; conflicts with FR-004/FR-006.

---

## Decision 3: Bot wish intent via extended classification + phrase gate

**Decision**: Extend `TextMessageIntent` with `wish_list`. Update `COMBINED_TEXT_INTENT_PROMPT` so not-yet-purchased messages (e.g. “I want to buy”, “買いたい”, “欲しい”, “wishlist”) classify as `wish_list`, not `expense`. Add a lightweight deterministic phrase gate before/around LLM classification to reduce false expense inserts on clear cues. On `wish_list`: run existing text (or image+text) extraction **without** `insert_expenses`, then budget-impact + confirm prompt.

**Rationale**: Spec FR-012/FR-016 require intercepting wish intent without breaking ordinary expenses. Existing three-way intent already sits before persist in `message_handler`.

**Alternatives considered**:
- Phrase-only detection without LLM — rejected; multilingual paraphrase coverage is weak alone.
- Post-parse classifier only — rejected; risk of inserting expense before redirect.

---

## Decision 4: Confirmation via existing reply-to yes/no (`pending_action`)

**Decision**: After proposing a wish add, persist confirmation with `pending_action = 'wish_list_add'` and pending payload (name, amount, category ids, optional link, language). User replies to that bot message; reuse `is_affirmative` / `is_cancel_pending` in `reply_edit.py`. Affirm → insert `wish_list_items` row; cancel/ignore → no row. No in-chat field edits (clarification session).

**Rationale**: Matches product confirmation UX and clarification “yes/no only”. Avoids LINE Quick Reply dependency (not used today).

**Alternatives considered**:
- LINE Quick Reply buttons only — rejected; inconsistent with reply-edit model and harder in `local_run`.
- Immediate add without confirm — rejected; contradicts spec.

---

## Decision 5: Hypothetical budget impact helper (reuse 015 math)

**Decision**: Add a small helper (e.g. `services/wish_list_budget.py`) that calls `fetch_budget_summary`, evaluates cascade candidates for the **candidate** category path with **spent + candidate_amount** (hypothetical), and returns: remaining now, remaining if purchased, and optional pace note when `compute_budget_health` / ahead check would be true **after** adding the amount. Do **not** use `maybe_prepend_budget_pace_warning` as-is (that assumes post-insert spend).

**Rationale**: Clarification requires remaining always (when budgeted) and pace only when ahead. Reusing `get_budget_summary` + pace math keeps bot aligned with `/budget` UI.

**Alternatives considered**:
- Only template “this costs ¥X” — rejected; underuses existing budget system.
- Insert-then-delete expense to reuse pace prepend — rejected; dangerous and races with real data.

---

## Decision 6: Image + wish text = combined handler inputs; LINE image-alone stays expense

**Decision**: Support wish extraction from image when **both** image bytes and wish-intent text are available in one processing call (extend `local_run.py` to allow `--image` with `--text` containing wish intent; pass accompanying text into image pipeline). Live LINE `ImageMessage` has no caption — image-alone continues through existing expense image flow. Users express wish intent in a **text** message (with name/price/URL as needed).

**Rationale**: Spec mentions image + “not bought yet” text; LINE webhooks do not attach captions to images. Combined harness path covers QA; text-primary path covers production.

**Alternatives considered**:
- Infer wish from image-only — rejected; no reliable “not purchased” signal.
- Correlate consecutive image+text messages by timestamp — deferred; fragile across groups.

---

## Decision 7: Execute creates expense then marks item executed (web API)

**Decision**: `POST /api/wish-list/[id]/execute` accepts editable fields (description/name, amount, category, expense_date, optional link ignored for expense). Transactional flow: insert expense (`wish_list_item_id` set, `expense_date` from body defaulting today) → update item `status=executed`, `executed_expense_id`, clear active sort participation. Reject if item not active.

**Rationale**: Clarifications: web-only execute; editable date default today; executed view is expense-centric.

**Alternatives considered**:
- Mutate wish row into an expense row — rejected; expenses already have a mature schema.
- Bot execute — out of scope per clarification.

---

## Decision 8: Web access and nav patterns

**Decision**: Mirror periodic/budget: `web/src/lib/wish-list/*`, Route Handlers under `/api/wish-list`, page at `/(app)/wish-list`, `assertTenantAccess`, SideDrawer nav + i18n keys. Expense tag in `ExpenseRowItem` when `wish_list_item_id` is non-null (same pill style as merchant/category tags).

**Rationale**: Consistency with features 011/012 reduces UX and auth drift.

**Alternatives considered**:
- Embed wish list under dashboard expenses page only — rejected; spec asks for a dedicated maintain page with ordering/execute.
