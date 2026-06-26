# Implementation Plan: Tenant Category Memory

**Branch**: `013-tenant-category-memory` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Per-tenant merchant→category memory to improve LINE bot category guesses. LLM merchant extraction, YAML alias normalization, weight-based skip of category LLM, learning from corrections and repeat logs, backfill from history, analytics columns. No web UI.

## Summary

Add **`category_merchant_memory`** table scoped by `(tenant_type, tenant_id, merchant_key)` and provenance columns on **`expenses`**. New bot modules **`merchant_extract`**, **`merchant_normalize`**, **`category_memory`** orchestrate: LLM extract merchant → normalize key → tenant lookup → skip **`classify_expense`** when `weight ≥ 1.0` → else category LLM + seed memory (`+0.25`). Reply-edits record **`user_correction`** (`weight=1.0`); repeat logs without prior category edit apply **`silent_confirm`** (`+0.5`). Ship **`data/merchant_aliases_ja.yaml`** (60+ Japanese chains). One-time **`scripts/backfill_category_memory.py`** seeds from existing expenses. RPC **`get_category_accuracy_stats`** for SC-001/SC-002.

## Technical Context

**Language/Version**: Python 3.11+ (LINE bot); SQL (Supabase Postgres migrations)

**Primary Dependencies**: Existing `GeminiClient`, `classify_expense`, `resolve_code`, `TenantContext`, `reply_edit`, `expense_repository`, `usage_metering`

**Storage**: Supabase Postgres — `category_merchant_memory`; `expenses` delta columns; `get_category_accuracy_stats` RPC

**Testing**: pytest for `merchant_normalize`, `merchant_extract` (mocked LLM), `category_memory` weight logic, `classify_expense_with_memory` integration; migration SQL smoke; manual quickstart

**Target Platform**: LINE bot (Cloud Run) + Supabase hosted Postgres

**Performance Goals**: Memory lookup + merchant LLM add ≤500ms p95 acceptable; category LLM skipped when `weight ≥ 1.0`

**Constraints**:
- Per-tenant memory only (no cross-tenant)
- Merchant key only (no amount dimension)
- Generic descriptions always category LLM; no memory
- Confirmation label unchanged for memory hits
- No web UI / no RLS on memory table v1
- Receipt `store_name` deferred to 014

**Scale/Scope**: Household users; hundreds of memory rows per tenant; YAML ~60–100 merchant keys

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Split `merchant_extract`, `merchant_normalize`, `category_memory`; single orchestrator in `categorize.py` |
| Test-First Delivery | pytest for normalize weights, memory skip threshold, correction overwrite, silent confirm on repeat log |
| User Experience Consistency | Same confirmation copy; no new user-facing modes |
| Performance & Reliability | DB lookup before LLM; graceful fallback if memory/merchant LLM fails |
| Observability & Feedback | `category_source` on expenses; stats RPC; structured logs on memory hit/miss |

**Gate**: PASS

**Post-design re-check**: PASS — extends existing categorize/reply-edit paths; no breaking API changes.

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  LINE message / receipt                                         │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  message_handler._enrich_and_persist_items                      │
│    classify_expense_with_memory(item, gemini, tenant)             │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
        ┌────────────────────┴────────────────────┐
        ▼                                         ▼
┌───────────────────┐                   ┌───────────────────────┐
│ merchant_extract  │                   │ category_merchant_    │
│ (LLM)             │                   │ memory (Supabase)     │
└─────────┬─────────┘                   └───────────┬───────────┘
          ▼                                         │
┌───────────────────┐                               │
│ merchant_normalize│◄── data/merchant_aliases_ja.yaml
│ + generic denylist│                               │
└─────────┬─────────┘                               │
          ▼                                         ▼
     merchant_key? ──lookup──► weight≥1.0? ──yes──► memory guess
          │ no                      │ no
          └──────────► classify_expense (LLM) ◄─────┘
                             │
                             ▼
                    insert expenses (+ guess_code, source)
                             │
          ┌──────────────────┴──────────────────┐
          ▼                                     ▼
   reply_edit category change            next log same merchant
   → record_user_correction              → silent_confirm +0.5
```

### Classification flow

1. Parse expense item (existing assist/receipt paths).
2. `extract_merchant_name` (LLM, `merchant_extract` scope).
3. `normalize_merchant_key` → skip if generic.
4. Lookup `category_merchant_memory` for tenant.
5. If `weight >= 1.0` and code valid → return guess, `source=memory`, empty alternatives.
6. Else `classify_expense` → `source=llm`; upsert `+0.25`.
7. If prior expense for merchant had unchanged guess → `+0.5` silent confirm.
8. Persist expense with `category_guess_code`, `category_source`.

### Learning flow

| Event | Memory update |
| ----- | ------------- |
| Category LLM used | `+0.25` llm |
| User category reply-edit | `weight=1.0`, overwrite code |
| New log, prior same-merchant expense uncorrected | `+0.5` silent_confirm |
| Backfill script | up to `1.0`, `last_source=backfill` |

## Project Structure

### Documentation

```text
specs/013-tenant-category-memory/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── appendix-merchant-alias-seed.md
├── contracts/
│   ├── categorize-memory.md
│   └── supabase-schema-delta.md
└── tasks.md                    # /speckit-tasks
```

### Source Code

```text
data/
  merchant_aliases_ja.yaml          # NEW — 60+ Japanese chain variants

supabase/migrations/
  20260628120000_category_merchant_memory.sql

services/
  merchant_extract.py               # NEW — LLM merchant_name JSON
  merchant_normalize.py             # NEW — YAML aliases, denylist, key
  category_memory.py                # NEW — lookup, upsert, weights
  categorize.py                     # classify_expense_with_memory()
  message_handler.py                # wire orchestrator + provenance
  reply_edit.py                     # record_user_correction hook
  expense_repository.py             # category_guess_code, category_source

scripts/
  backfill_category_memory.py       # NEW — idempotent history seed

tests/
  test_merchant_normalize.py
  test_merchant_extract.py
  test_category_memory.py
  test_categorize_memory.py
  test_message_handler_persistence.py  # extend
  test_reply_edit.py                   # extend correction → memory
```

## Implementation Phases

### Phase 1 — Schema & static data (blocking)

1. Migration: `category_merchant_memory` table + expense columns + `get_category_accuracy_stats` RPC.
2. `data/merchant_aliases_ja.yaml` per appendix (konbini, supermarkets, drugstores, dining, transport, etc.).
3. `merchant_normalize.py` with tests (alias hit, branch strip, generic denylist).

### Phase 2 — Merchant LLM extract

1. `merchant_extract.py` + JSON schema validation.
2. pytest with mocked Gemini responses.
3. Register `merchant_extract` in usage metering tests if needed.

### Phase 3 — Memory repository

1. `category_memory.py`: lookup, upsert_llm_seed, record_user_correction, apply_silent_confirm, find_prior_expense.
2. pytest for weight math and threshold 1.0 skip.

### Phase 4 — Classification orchestration

1. `classify_expense_with_memory` in `categorize.py`.
2. Wire `message_handler._enrich_and_persist_items`.
3. Extend `ExpenseInsertRow` / `build_insert_row` with provenance fields.
4. Integration tests: memory hit skips categorize mock.

### Phase 5 — Reply-edit learning

1. Hook `apply_edit_intent` after category `update_expense_fields`.
2. Tests: correction sets weight 1.0; group tenant last-writer wins.

### Phase 6 — Backfill & analytics

1. `scripts/backfill_category_memory.py` (heuristic merchant, no LLM).
2. Document run in quickstart; dry-run mode.
3. Verify `get_category_accuracy_stats` against sample data.

### Phase 7 — Verification

1. Full pytest suite green.
2. Manual quickstart: correct merchant → repeat log skips LLM.
3. Group tenant shared memory check.
4. Generic `食費` always calls category LLM.

## Risks & Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Extra LLM call per expense | Skip category LLM when memory confident; merge extract into assist later |
| Backfill heuristic mismatches LLM keys | Live path uses LLM; backfill improves over time via corrections |
| Group last-writer conflicts | Accepted per spec; silent overwrite |
| Orphan memory after category delete | `resolve_code` fallback to LLM |
| Multi-line receipts weak keys until 014 | Document limitation; 014 adds `store_name` |
| Silent confirm double-count | Only on new expense log comparing to single prior expense |

## Dependencies

- **004** — `classify_expense`, expenses table
- **005** — reply-edit category updates
- **006** — tenant scope on expenses
- **007** — usage metering scopes
- **010** — tenant `resolve_code`
- **014** (future) — receipt `store_name`

## Suggested Next Command

After plan approval: `/speckit-tasks` to generate `tasks.md`.
