# Implementation Plan: Supabase Expense Storage & Budget Analysis

**Branch**: `004-supabase-expense-storage` | **Date**: 2026-06-06 (revised) | **Spec**: `/specs/004-supabase-expense-storage/spec.md`

**Input**: Feature specification + user direction: target Supabase `https://nyuenufldaqsjybjhawl.supabase.co`; **LLM produces JSON only — app executes predefined DB operations, never LLM-generated SQL.**

## Summary

Persist each detected expense to **Supabase Postgres** after the existing detection pipeline succeeds, with **LLM auto-categorization** (JSON output) against a **seeded Japanese-household taxonomy**. The **application layer** validates JSON, maps category codes to DB IDs, and inserts via **fixed repository methods** — no dynamic or LLM-authored queries. Replies include guessed category + up to three alternatives; user corrections are not persisted in v1. Schema supports future JST monthly/yearly analysis (RPC functions) and budget rows (structure only). Idempotency: **LINE message ID** (production) or **fresh UUID per console run**.

## Technical Context

**Language/Version**: Python 3.11+ (3.13 in CI/Docker)

**Primary Dependencies**: FastAPI, line-bot-sdk, google-genai, python-dotenv, **supabase**, jsonschema, pytest

**Storage**: Supabase Postgres — `https://nyuenufldaqsjybjhawl.supabase.co`; service role key server-side only

**Testing**: pytest with mocked Supabase client; JSON schema tests for LLM outputs; RPC rollup fixture tests

**Target Platform**: Google Cloud Run + local console harness

**Project Type**: web-service + CLI dev harness

**Performance Goals**: Categorization JSON + insert adds ≤2s p95; rollup RPCs <5s for 1k rows/user

**Constraints**:
- **LLM never touches database** — JSON in, validated, repository writes out ([llm-db-boundary.md](./contracts/llm-db-boundary.md))
- Storage failure must not block reply (FR-011)
- No budget impact in replies (FR-010)
- JST for calendar grouping
- RLS on user tables; service role for bot

**Scale/Scope**: ~50–80 seeded category nodes; predefined repository API (4 operations in v1)

## Supabase Project Status (MCP verified 2026-06-06)

| Item | Value |
| ---- | ----- |
| **MCP server** | `project-0-linebot-money-tracker-supabase` |
| **Project URL** | `https://nyuenufldaqsjybjhawl.supabase.co` ✓ |
| **`public` tables** | **None** (blank — ready for expense migration) |
| **Migrations applied** | **None** |
| **Installed extensions** | `uuid-ossp`, `pgcrypto`, `pg_stat_statements`, `supabase_vault` (defaults) |

**Next step for implement**: Apply `supabase/migrations/20260606120000_expense_schema.sql` via MCP `apply_migration` or Dashboard SQL editor.

No RLS advisories yet (no user tables). Enable RLS on `expenses` and `monthly_budgets` when migration is applied.

## Architecture: LLM JSON → App → Predefined DB ops

```text
┌─────────────┐     JSON      ┌──────────────────┐   fixed insert   ┌──────────┐
│ Gemini LLM  │ ────────────► │ message_handler  │ ───────────────► │ Supabase │
│ (no SQL)    │   expenses +  │ + categorize     │  expense_repo    │ Postgres │
└─────────────┘   categories  │ + jsonschema     │  .insert_expenses│          │
                              └──────────────────┘   .rpc(totals)    └──────────┘
```

1. **Detect** expenses → JSON array (existing pipeline)
2. **Categorize** each item → JSON `{guessed_category_code, alternatives}`
3. **Validate** both against jsonschema
4. **Map** codes → `category_nodes.id` via cached taxonomy (app lookup)
5. **Insert** via `expense_repository.insert_expenses()` only
6. **Reply** formatted in Python (not LLM SQL)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Strict LLM/DB boundary; repository with fixed API |
| Test-First Delivery | Test JSON validation, code→UUID mapping, insert idempotency, no LLM SQL paths |
| User Experience Consistency | Reply templates in `message_handler` |
| Performance & Reliability | Cached taxonomy; async insert; Gemini retry existing |
| Observability & Feedback | Log JSON parse failures, insert results, category codes |
| Secrets | Service role server-only |

**Post-design re-check**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/004-supabase-expense-storage/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── llm-db-boundary.md      # NEW — LLM JSON vs predefined queries
    ├── supabase-schema.md
    ├── expense-persistence.md
    ├── categorization-reply.md
    └── environment-variables.md
```

### Source Code (repository root)

```text
services/
  message_handler.py             # orchestrate detect → categorize → insert → reply
  message_context.py             # line_user_id, source_message_id
  line_event.py                  # extract user + message ids
  categorize.py                  # LLM → CategoryGuess JSON only
  category_taxonomy.py           # load/cache category_nodes; code → node
  expense_repository.py          # insert_expenses + RPC wrappers ONLY
  supabase_client.py             # client factory
data/category_taxonomy_ja.yaml   # seed source for migration
supabase/migrations/
  20260606120000_expense_schema.sql
tests/
  test_categorize.py             # JSON schema / code validation
  test_expense_repository.py     # mock Supabase; no dynamic SQL
  test_message_handler_persistence.py
```

## Implementation Approach

### 1. Supabase schema + predefined RPCs

Migration creates tables + **fixed functions**:
- `monthly_expense_total(p_line_user_id, p_year, p_month, p_category_node_id, p_currency)`
- `yearly_expense_total(p_line_user_id, p_year, p_category_node_id, p_currency)`

See [data-model.md](./data-model.md) and [supabase-schema.md](./contracts/supabase-schema.md).

### 2. Category taxonomy cache

On startup (or first use): `load_category_taxonomy()` → dict keyed by `code`. All LLM category codes validated against this map before insert.

### 3. Categorization (`services/categorize.py`)

- Input: expense `{description, amount, currency}` + compact taxonomy code list in prompt
- Output: **JSON only** — `CategoryGuess` dataclass
- Invalid / missing codes → `unknown`

### 4. Persistence (`services/expense_repository.py`)

**Only** allowed write path:

```python
def insert_expenses(rows: list[ExpenseInsertRow]) -> PersistResult:
    client.table("expenses").insert([r.to_dict() for r in rows]).execute()
```

App computes `category_l1/l2/l3_id` and `assigned_level` from taxonomy tree — not LLM.

### 5. Message handler integration

```python
items = detect_expenses(...)
guesses = [await categorize(item) for item in items]
rows = [build_insert_row(ctx, item, guess) for item, guess in zip(items, guesses)]
persist_result = insert_expenses(rows)  # never raises to user path
return format_expense_reply(items, guesses)
```

### 6. Environment

| Profile | Supabase |
| ------- | -------- |
| Console | Optional (skip insert if unset) |
| Webhook / Cloud Run | Required |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| Denormalized category_l* on expenses | Rollup RPC simplicity | Dynamic SQL rejected by design |
| Separate categorize + repository | LLM/DB boundary + testability | Monolithic handler hides contract |

## Phase Outputs

- [research.md](./research.md) — includes LLM/DB boundary decision
- [data-model.md](./data-model.md)
- [contracts/](./contracts/) — includes `llm-db-boundary.md`
- [quickstart.md](./quickstart.md)

**Next command**: `/speckit-tasks`
