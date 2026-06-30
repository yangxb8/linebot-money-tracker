# Implementation Plan: Budget Pace Alert in LINE Bot Replies

**Branch**: `015-budget-pace-alert` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: When a user logs or reply-edits an expense, evaluate budget pace at all defined cascade levels (L2 → L1 → total), warn at the **lowest ahead-of-pace level only**, prepend an emoji LLM-generated (with template fallback) reminder with daily allowance before the normal confirmation or edit summary.

## Summary

Add Python budget-pace services that call existing `get_budget_summary` RPC, port web health math, and prepend a localized warning to LINE bot replies after expense persist and category/amount reply-edits. No schema changes. Warnings align with web `/budget` pace definition (`pace_ratio > 1`). LLM generates conversational text from computed facts; templates ensure FR-013 graceful degradation.

## Technical Context

**Language/Version**: Python 3.11+ (LINE bot at repo root)

**Primary Dependencies**: FastAPI/uvicorn (webhook), `line-bot-sdk`, existing `GeminiClient` / `metered_gemini`, `supabase-py` service-role client

**Storage**: Supabase Postgres — read-only use of `monthly_budgets`, `expenses`, `category_nodes`; RPC `get_budget_summary` (from 012)

**Testing**: `pytest` — unit tests for pace math, lowest-level selection, prepend helper; integration mocks for RPC; update `test_message_handler_persistence` / reply-edit tests

**Target Platform**: LINE webhook (`main.py`) + `local_run.py` console harness

**Performance Goals**: Pace evaluation adds ≤500ms p95 per reply (one RPC + optional one short Gemini call); failure path adds 0ms user-visible delay

**Constraints**:
- JPY only
- No new migrations
- Must not block confirmation on pace/LLM failure (FR-013)
- Reuse 012 pace formula and fiscal month from RPC
- Group vs personal tenant scoping
- ja/en/zh reply languages

**Scale/Scope**: Household users; 0–3 budget levels evaluated per expense path; 1 RPC per distinct fiscal month per reply

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | New `services/budget_pace*.py` modules; health math isolated and mirrored from TS with tests |
| Test-First Delivery | `tests/test_budget_pace.py` before/with implementation; extend handler/reply-edit tests |
| User Experience Consistency | Emoji lead-in, blank-line separation, ja/en/zh; predictable prepend position |
| Performance & Reliability | Single RPC; try/except wrapper; template fallback if LLM slow/fails |
| Observability & Feedback | Log RPC/LLM failures at warning level; pace warnings surface category + daily ¥ |

**Gate**: PASS

**Post-design re-check**: PASS — read-only budget access; no change to expense ingestion contract; optional LLM scoped and metered.

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  LINE user                                                       │
└────────────┬────────────────────────────────────────────────────┘
             │ text / image / reply-edit
             ▼
┌────────────────────────────┐     ┌──────────────────────────────┐
│  message_handler.py        │     │  reply_edit.py               │
│  _enrich_and_persist_items │     │  apply_edit_intent (update)  │
└────────────┬───────────────┘     └──────────────┬───────────────┘
             │ after persist                       │ after category/amount change
             └──────────────────┬──────────────────┘
                                ▼
             ┌──────────────────────────────────────┐
             │  maybe_prepend_budget_pace_warning()   │
             │  services/budget_pace.py               │
             └────────────┬─────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   get_budget_summary   health math   category names
   (Supabase RPC)       (Python port)  (category_nodes)
                          │
                          ▼
             ┌──────────────────────────────────────┐
             │  format warning (LLM or i18n)       │
             │  prepend + "\n\n" + confirmation     │
             └──────────────────────────────────────┘
```

### Evaluation flow (lowest-ahead rule)

```text
expense persisted → budget_month from expense_date
→ RPC summary → build candidates [L2?, L1?, total?]
→ for each in order: if pace_ratio > 1 → warn this level, stop
→ format → prepend
```

## Project Structure

### Documentation (this feature)

```text
specs/015-budget-pace-alert/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── budget-pace-evaluation.md
│   └── budget-pace-reply.md
└── tasks.md             # Phase 2 (/speckit-tasks — not yet created)
```

### Source Code (repository root)

```text
services/
├── budget_pace.py           # RPC fetch, health math, candidate build, evaluate
├── budget_pace_i18n.py      # Template fallback strings (ja/en/zh)
├── budget_pace_prompt.py    # LLM prompt builder
├── message_handler.py       # Hook after persist (modify)
└── reply_edit.py            # Hook after update (modify)

tests/
├── test_budget_pace.py      # Unit tests (new)
├── test_message_handler_persistence.py  # Update pace expectations
└── test_reply_edit.py       # Reply-edit prepend cases
```

**Structure Decision**: Extend existing Python `services/` layout; no `web/` changes required for v1.

## Phase 0: Research

Completed — see [research.md](./research.md).

Key decisions:
1. Reuse `get_budget_summary` RPC
2. Port `computeBudgetHealth` to Python
3. Multi-level check, lowest-ahead warning only
4. LLM wording + i18n fallback
5. Hook after persist in `message_handler` and `reply_edit`
6. Fiscal month from RPC (not hardcoded calendar)

## Phase 1: Design & Contracts

Completed artifacts:
- [data-model.md](./data-model.md) — derived types and flow
- [contracts/budget-pace-evaluation.md](./contracts/budget-pace-evaluation.md) — service API
- [contracts/budget-pace-reply.md](./contracts/budget-pace-reply.md) — prepend + LLM contract
- [quickstart.md](./quickstart.md) — manual verification

### Implementation notes for `/speckit-tasks`

| Task area | Files | Priority |
| --------- | ----- | -------- |
| Pace math + RPC | `services/budget_pace.py` | P1 |
| i18n fallback | `services/budget_pace_i18n.py` | P1 |
| LLM prompt | `services/budget_pace_prompt.py` | P2 |
| New expense hook | `services/message_handler.py` | P1 |
| Reply-edit hook | `services/reply_edit.py` | P1 |
| Unit tests | `tests/test_budget_pace.py` | P1 |
| Integration tests | handler + reply-edit tests | P1 |
| Metering | `services/metered_gemini.py` — add `budget_pace` op if needed | P2 |

### Category name resolution

Query `category_nodes` for `id IN (...)` when formatting warnings, or pass `name_ja` from enrichment if already available post-categorize.

### Multi-item expenses

Deduplicate by `(assigned_level, category_node_id, category_l1_id, expense_date month)` before evaluating; concatenate multiple warnings with newline when distinct paths qualify (FR-012).

## Complexity Tracking

> No constitution violations requiring justification.

| Consideration | Mitigation |
| ------------- | ---------- |
| Optional LLM adds latency | Short prompt; template fallback; async with timeout budget |
| Python/TS health drift | Shared test vectors copied from `health.test.ts` |

## Phase 2

**Not in scope for `/speckit-plan`** — run `/speckit-tasks` to generate `tasks.md`.
