# Implementation Plan: Item-Level Category Memory for Receipts

**Branch**: `cursor/item-category-memory-e56a` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/018-item-category-memory/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Extend tenant category memory so **receipt/image** expense lines remember categories by **normalized item key**, preferencing **(store, item)** then **item-only** (correction-seeded), instead of merchant-only hard-skip that forces one category onto an entire mixed-goods cart. Keep **013 merchant-only memory** for free-text logs. On classify miss, pass merchant memory as a **soft prior**. Backfill **store+item** only. Skip category LLM when item-memory weight ≥ 1.0.

## Technical Context

**Language/Version**: Python 3.11+ (LINE bot); SQL (Supabase Postgres migrations)

**Primary Dependencies**: Existing `classify_expense_with_memory`, `category_memory`, `merchant_resolve`, `receipt_store_name`, `reply_edit`, `expense_repository`, `GeminiClient`, usage metering

**Storage**: Supabase Postgres — new `category_item_memory` table; optional `expenses.category_source` check expansion (`item_memory`); existing `category_merchant_memory` unchanged for text path

**Testing**: pytest for `item_normalize`, item-memory lookup/write rules, receipt vs text branching, soft prior prompt, reply-edit no merchant overwrite on receipt lines, backfill dry-run; golden fixtures for 島忠-style mixed cart

**Target Platform**: LINE bot (Cloud Run) + Supabase hosted Postgres

**Project Type**: Chat bot + shared Supabase backend (web unchanged for v1)

**Performance Goals**: Per-line item-memory lookup + optional classify; no worse than current receipt latency when weight ≥ 1.0 skip fires; soft-prior classify remains one categorize LLM call per line on miss

**Constraints**:
- Receipt/image path only for item memory (incl. single-line receipt photos)
- Text path keeps merchant-only 013 behavior
- Item-only rows written only on explicit category correction
- Merchant hard-skip must not apply on receipt/image lines
- No web UI; service-role writes (same pattern as 013 memory table)
- Deterministic item-key rules only (no embeddings)

**Scale/Scope**: Household tenants; hundreds–thousands of item-memory rows per tenant after backfill; typical receipts 1–20 lines

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | New `item_normalize` + item-memory APIs alongside existing `category_memory`; orchestrator stays in `categorize.py` with explicit `memory_mode` |
| Test-First Delivery | pytest before behavior change: normalize, lookup order, write gates, soft prior, reply-edit isolation, text regression |
| User Experience Consistency | Same confirmation “guess” copy; multi-category subtotals already via 017 |
| Performance & Reliability | DB lookup before LLM; fail-open to classify on memory errors; merchant soft prior never hard-assigns |
| Observability & Feedback | Extend `category_source` with `item_memory`; log hit kind (`store_item` / `item_only` / soft-prior miss) |

**Gate**: PASS

**Post-design re-check**: PASS — additive table + branched classify/reply-edit; no breaking web APIs; text path preserved.

## Project Structure

### Documentation (this feature)

```text
specs/018-item-category-memory/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── categorize-item-memory.md
│   ├── item-normalize.md
│   └── supabase-schema-delta.md
└── tasks.md                 # /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
services/
├── categorize.py              # Branch receipt vs text; soft prior; item lookup order
├── category_memory.py         # Keep merchant APIs; add item-memory helpers or thin facade
├── item_normalize.py          # NEW — deterministic item_key from description
├── reply_edit.py              # Correction writes item memory; no merchant rewrite on receipt lines
├── message_handler.py         # Pass memory_mode=item for image/receipt pipeline
└── receipt_parser.py          # Reuse clean_receipt_description; item_normalize builds on it

scripts/
├── backfill_category_memory.py       # unchanged (merchant)
└── backfill_category_item_memory.py  # NEW — store+item only

supabase/migrations/
└── YYYYMMDDHHMMSS_category_item_memory.sql

tests/
├── test_item_normalize.py
├── test_category_item_memory.py
├── test_categorize_item_memory.py
└── test_reply_edit.py               # extend receipt correction cases
```

**Structure Decision**: Extend the existing bot `services/` + `tests/` + Supabase migrations layout. No web changes in v1. Prefer a dedicated `category_item_memory` table over overloading `category_merchant_memory` so uniqueness and write rules stay clear.

## Phase 0: Research (output: research.md)

See [research.md](./research.md) — resolved: table shape, receipt detection, soft prior, provenance values, normalize rules, reply-edit isolation, backfill eligibility.

## Phase 1: Design (output: data-model.md, contracts/, quickstart.md)

See linked artifacts below. Agent context (`.cursor/rules/specify-rules.mdc`) updated to point at this plan/quickstart.
