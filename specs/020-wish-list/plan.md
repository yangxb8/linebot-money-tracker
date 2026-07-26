# Implementation Plan: Wish List

**Branch**: `cursor/wish-list-b2d9` | **Date**: 2026-07-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/020-wish-list/spec.md`

## Summary

Add a per-ledger **Wish List** for planned purchases. The web dashboard gets a new page for CRUD, manual priority ordering, sort-by-created-time/price, execute-to-expense (editable confirm including date), an executed filter (expense-centric), and a wish-list tag on expense cards. The LINE bot detects not-yet-purchased intent, replies with **budget impact** (remaining now / remaining if purchased, plus pace note when ahead), and yes/no confirmation to add — without logging an expense. Execute is web-only in v1.

## Technical Context

**Language/Version**: Python 3.11+ (LINE bot); TypeScript/React (Next.js web); SQL (Supabase Postgres)

**Primary Dependencies**: Existing tenant context, intent classification (`services/intent.py`), AI parse assist, confirmation/reply-edit affirm patterns, `services/budget_pace.py` + `get_budget_summary` RPC, web tenant switcher / `assertTenantAccess`, expense list UI (`ExpenseRowItem`)

**Storage**: Supabase Postgres — new `wish_list_items` table (tenant-scoped); `expenses.wish_list_item_id` FK (mirror `periodic_schedule_id`); confirmation `pending_action` value for bot add

**Testing**: pytest for intent branch, budget-impact helper, confirm-add / decline, no-expense-on-wish; web vitest/lint for API validation and types where patterns exist; manual quickstart for end-to-end

**Target Platform**: LINE bot (Cloud Run) + Next.js web dashboard + Supabase

**Project Type**: Chat bot + web dashboard + shared Supabase backend

**Performance Goals**: Wish CRUD is simple indexed tenant reads/writes; bot wish path adds at most one budget summary RPC + existing parse/classify LLM work (no expense insert); list reorder is a bounded batch update of `sort_order`

**Constraints**:
- Per-ledger isolation (`tenant_type` + `tenant_id`); group chat writes to group ledger
- Bot must not create expenses on wish intent; ordinary expenses unchanged
- Bot confirm is yes/no only; edits are web-only after add
- Execute is web-only; expense date defaults to today (editable)
- Executed filter shows final expense values + link (not pre-execute snapshot)
- Budget impact: remaining always when budgeted; pace note only when hypothetical spend is ahead
- JPY only; reuse existing categories
- Do not overload `category_source` for wish origin — use FK like periodic expenses

**Scale/Scope**: Household tenants; modest active wish lists (tens of items typical); one list per ledger

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | New `wish_list` service/lib modules; reuse tenant, confirmation, budget_pace, expense insert patterns; no parallel budget system |
| Test-First Delivery | pytest for intent routing, impact math, confirm-add before wiring webhook; web validation tests alongside API |
| User Experience Consistency | Bot replies follow existing confirm structure + i18n; web page matches SideDrawer nav / tenant switcher patterns; expense tag mirrors merchant/category pills |
| Performance & Reliability | Fail-open budget impact (still offer add if summary unavailable); wish path skips expense insert; validate inputs before persist |
| Observability & Feedback | Log wish intent detection, pending_action, execute outcome; clear validation errors on web |

**Gate**: PASS (pre- and post-design)

## Project Structure

### Documentation (this feature)

```text
specs/020-wish-list/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── wish-list-api.md
│   ├── wish-list-bot.md
│   └── supabase-schema-delta.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # /speckit-tasks (not created here)
```

### Source Code

```text
supabase/migrations/YYYYMMDDHHMMSS_wish_list_items.sql

# Bot
services/wish_list.py              # repository + execute helpers (or split)
services/wish_list_budget.py       # hypothetical remaining + pace note
services/intent.py                 # extend TextMessageIntent + prompt
services/message_handler.py        # branch before expense persist
services/reply_edit.py             # affirm/cancel pending wish_list_add
services/confirmation_repository.py  # pending_action support
local_run.py                       # --image + --text wish path if needed
tests/test_wish_list*.py

# Web
web/src/app/(app)/wish-list/page.tsx
web/src/components/wish-list/*
web/src/lib/wish-list/{server,client,types,validation}.ts
web/src/app/api/wish-list/route.ts
web/src/app/api/wish-list/[id]/route.ts
web/src/app/api/wish-list/reorder/route.ts
web/src/app/api/wish-list/[id]/execute/route.ts
web/src/components/SideDrawer.tsx   # nav entry
web/src/components/expenses/ExpenseRowItem.tsx  # wish tag
web/src/lib/expenses/types.ts
web/src/lib/i18n/messages.ts
```

**Structure Decision**: Extend the existing monorepo layout (Python bot at repo root + `web/` Next.js + `supabase/migrations`). No new top-level package.

## Implementation Approach

1. **Schema**: Create `wish_list_items` + `expenses.wish_list_item_id`; RLS/access consistent with periodic/expenses tenant model (service role from bot; session + `assertTenantAccess` from web).
2. **Web CRUD + order/sort**: Wish List page with active default, manual reorder API, client sort modes (priority / created / price), validation.
3. **Execute**: Confirm form (pre-fill + editable date defaulting today) → insert expense with `wish_list_item_id` → mark item `executed` + store `executed_expense_id`.
4. **Executed filter + tag**: Filter query joins/reads expense fields; `ExpenseRowItem` shows wish tag when `wish_list_item_id` present.
5. **Bot intent**: Extend classification for `wish_list` (plus phrase gate for clear EN/JA cues); extract via existing assist parsers **without** insert; compute budget impact; save confirmation with `pending_action=wish_list_add`; yes/no via existing affirm/cancel.
6. **Tests + quickstart**: Cover happy paths and “ordinary expense unchanged”; document console + web manual flows.

## Complexity Tracking

> No constitution violations requiring justification.
