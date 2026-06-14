# Feature: Bulk Category Change via Reply

## Clarifications

### Session 2026-06-14

- Q: Same category for all targeted items? → A: Yes — one category applied to all targeted items
- Q: How should bulk category be triggered? → A: LLM interprets free-text intention; show interpreted action for YES confirmation before proceeding; if wrong, user replies to expense message again with clearer text
- Q: Confirmation after LLM shows 3 options? → A: User replies 1/2/3
- Q: Subset targeting? → A: Support `1 3 食品` and `1,3 食品` (space or comma)
- Q: Single-item free-text category? → A: Always show up to 3 options and require 1/2/3 pick

## User Stories

### US1 — Bulk category change (all items)

User replies to a multi-item confirmation with free text like `餐饮` without item numbers. LLM interprets intent, bot asks YES to confirm interpretation, then shows up to 3 taxonomy options; user picks 1/2/3; all active items receive the same category.

### US2 — Subset category change

User replies `1,3 交通` or `1 3 交通` to change category for items 1 and 3 only. Intent is explicit — skip interpretation confirm, show category options directly.

### US3 — Single-item free-text category

User replies `餐饮` on a single-item confirmation. Show category options (1/2/3) without interpretation confirm.

## Functional Requirements

- FR-001: Apply one selected category to all targeted active (non-deleted) items
- FR-002: No item numbers on multi-item → all active items (after LLM interpretation confirm)
- FR-003: Subset syntax: space- or comma-separated item numbers before category text
- FR-004: `map_category_from_text` LLM maps free text → up to 3 valid taxonomy codes
- FR-005: `pending_action` values: `confirm_intent`, `category_bulk`, `delete_all` (existing)
- FR-006: `pending_payload` stores interpretation summary, category query, options, target indices
- FR-007: Bare 1/2/3 still picks from snapshot alternatives immediately (unchanged)
- FR-008: Deterministic delete phrases unchanged

## State Machine

1. `confirm_intent` — awaiting YES; payload has `interpreted_action`, `category_query`, `target_line_item_indices`
2. On YES + `category_bulk` → map category → `category_bulk` pending with options
3. `category_bulk` — awaiting 1/2/3 pick
4. On 1/2/3 → update all targets → clear pending
