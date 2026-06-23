# Implementation Plan: Monthly Budget Manager

**Branch**: `012-monthly-budget-manager` | **Date**: 2026-06-23 | **Spec**: [spec.md](./spec.md)

**Input**: Web console feature to set monthly budgets (total, L1, L2) per personal or group ledger, automatically track spending from all expense sources with cascade bucket rules, show progress/health UI, and offer copy/suggest setup helpers.

## Summary

Evolve the placeholder **`monthly_budgets`** table to tenant scope with `budget_level` (`total` | `l1` | `l2`) and nullable `category_node_id` for the overall cap. Add RPC **`get_budget_summary`** plus SQL helper **`resolve_budget_bucket`** to compute spent on read from **`expenses`** (no materialized counters, no bot changes). Web UI adds **`/budget`** with total + expandable L1/L2 breakdown, progress bars, pace-based health coloring, and edit flow with child-sum suggestions. API at **`/api/budgets/*`** mirrors 010/011 tenant auth patterns. Shared **`lib/budget/`** module holds health math and cascade logic for tests and client preview.

## Technical Context

**Language/Version**: TypeScript / Node 20+ (Next.js 15 App Router); SQL (Supabase Postgres migrations)

**Primary Dependencies**: Next.js, `@supabase/supabase-js`, `@supabase/ssr`; existing tenant switcher, categories API, `can_access_tenant`, `monthly_expense_total` RPC from 004/015

**Storage**: Supabase Postgres — migrate `monthly_budgets`; new RLS policies; `get_budget_summary` + `resolve_budget_bucket` RPCs

**Testing**: Vitest for `lib/budget/health.ts` and `lib/budget/cascade.ts`; API route validation tests; SQL integration for bucket assignment + RLS cross-tenant deny; manual checklist in quickstart

**Target Platform**: Vercel (`web/`) + Supabase hosted Postgres

**Performance Goals**: Budget summary load ≤1s p95 for ≤500 expenses/month; save budget ≤2s; health computation <1ms client-side

**Constraints**:
- JPY only
- Calendar fiscal month (JST); custom start day deferred
- On-read spent aggregation (no expense triggers)
- Current month editable; prior months read-only in v1
- No bot budget CRUD or display
- Group members with dashboard access may edit group budgets (FR-019)

**Scale/Scope**: Household users; tens of category budgets per tenant; low write frequency (monthly setup)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Shared `lib/budget/` module; SQL in migrations; single summary RPC |
| Test-First Delivery | Vitest for cascade + health before UI; SQL bucket matrix; API validation tests |
| User Experience Consistency | ja/en/zh strings; mobile-first layout; drawer nav matches Categories/Periodic pattern |
| Performance & Reliability | Indexed tenant+month; on-read aggregation sufficient at household scale; no bot latency impact |
| Observability & Feedback | API error messages; pace labels for budget health; no PII in client logs |

**Gate**: PASS

**Post-design re-check**: PASS — spent derived from existing expense writes; no new ingestion paths; bot unchanged.

## Architecture

```text
┌──────────────────┐   drawer nav    ┌─────────────────────────────┐
│  /dashboard      │ ◄──────────────►│  /budget                    │
│  ExpenseList     │                 │  BudgetSummary + Editor     │
└────────┬─────────┘                 └──────────────┬──────────────┘
         │                                            │
         │  Supabase JS (read expenses — existing)    │  /api/budgets/*
         ▼                                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Supabase Postgres                                                   │
│  monthly_budgets (tenant-scoped, budget_level)                       │
│  expenses (unchanged — all ingestion paths)                          │
│  RPC get_budget_summary, resolve_budget_bucket                       │
│  RPC monthly_expense_total (suggestions)                             │
└──────────────────────────────────────────────────────────────────────┘
         ▲
         │ service role (bot/cron writes expenses only)
┌────────┴────────┐
│  LINE bot       │  no budget awareness in v1
│  Periodic cron  │
└─────────────────┘
```

### Budget view flow

1. User opens `/budget` with tenant from switcher.
2. `GET /api/budgets?tenant_type&tenant_id` calls `get_budget_summary`.
3. Client computes health color/labels via `lib/budget/health.ts`.
4. User edits limits; L1/total fields show suggested sums from children.
5. `PUT /api/budgets` upserts rows; response returns refreshed summary.

### Expense → budget flow (automatic)

1. Expense inserted/updated/deleted (bot, reply-edit, periodic cron).
2. No budget-side write.
3. Next `GET /api/budgets` recomputes spent via cascade rules.

### Cascade example

| Expense | Budgets set | Bucket |
| ------- | ----------- | ------ |
| L2 外食 ¥1,200 | L2 外食 limit | L2 外食 |
| L2 外食 ¥1,200 | L1 食費 only | L1 食費 |
| L2 食料品 ¥500 | Total only | Total |
| L1 住居 ¥80,000 | None | Unbudgeted |

Total progress bar (when total limit set) always uses **all** month expenses.

## Project Structure

### Documentation

```text
specs/012-monthly-budget-manager/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── supabase-schema-delta.md
    └── budget-api.md
```

### Source Code

```text
supabase/migrations/
  20260624120000_monthly_budgets_tenant.sql

web/src/
  app/
    (app)/budget/page.tsx
    api/budgets/
      route.ts                          # GET summary, PUT upsert
      copy-from-previous/route.ts       # POST
      suggestions/route.ts              # GET
  components/
    SideDrawer.tsx                      # add navBudget
    AppShell.tsx                        # budget title route
    budget/
      BudgetPage.tsx
      BudgetTotalCard.tsx
      BudgetCategoryTree.tsx
      BudgetRow.tsx                     # progress + health + edit
      BudgetEditor.tsx                  # inline/sheet edit
      BudgetEmptyState.tsx
  lib/budget/
    types.ts
    health.ts                           # pace ratio + tone
    cascade.ts                          # TS mirror of resolve_budget_bucket
    format.ts                           # yen, %, daily allowance text
    validation.ts
    server.ts                           # RPC wrappers, tenant access
  lib/i18n/messages.ts                  # navBudget, pace labels, etc.

web/src/lib/budget/__tests__/
  health.test.ts
  cascade.test.ts
```

## Implementation Phases

### Phase 1 — Schema & RPC (blocking)

1. Migration: tenant columns, `budget_level`, nullable total row, indexes, RLS.
2. `resolve_budget_bucket` SQL function.
3. `get_budget_summary` RPC returning JSON per contract.
4. SQL tests: cascade matrix, cross-tenant deny.

### Phase 2 — Shared budget library

1. `lib/budget/cascade.ts` + Vitest (parity with SQL cases).
2. `lib/budget/health.ts` + Vitest (day-1 neutral, over-pace, on-track).
3. `lib/budget/format.ts` for remaining/daily allowance strings.

### Phase 3 — API routes

1. `GET/PUT /api/budgets` with validation and tenant guard.
2. `POST /api/budgets/copy-from-previous`.
3. `GET /api/budgets/suggestions` using `monthly_expense_total`.
4. Route handler tests.

### Phase 4 — Web UI

1. Drawer nav + `/budget` page shell.
2. `BudgetTotalCard` — total limit, progress, health, edit.
3. `BudgetCategoryTree` — expandable L1/L2 rows.
4. Editor with child-sum suggestions and buffer override.
5. Copy-from-previous + per-row suggest buttons (P3).
6. Empty/unlimited state, unbudgeted callout, i18n.

### Phase 5 — Verification

1. Vitest cascade + health suites green.
2. Manual quickstart checklist (personal, group, reply-edit, periodic).
3. Confirm mid-month first budget includes existing expenses (FR-015).

## Risks & Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Total vs cascade spent confusion | Document in API contract; total bar = all spend; L1/L2 = assigned only |
| Legacy `monthly_budgets` empty | Migration is additive; no data loss risk |
| Summary RPC slow at scale | Index `(tenant_type, tenant_id, expense_date)` exists; revisit materialized view if needed |
| Orphan budget after category delete | Filter in RPC; UI warning to clear stale row |
| Group concurrent budget edits | Last-write-wins on PUT; acceptable per 010/011 |

## Dependencies

- **009-expense-web-dashboard**: auth, tenant switcher — complete
- **010-tenant-category-editor**: L1/L2 tree, drawer nav — complete
- **011-periodic-expense-scheduler**: auto-logged expenses in same ledger — complete
- **004-supabase-expense-storage**: `monthly_budgets` placeholder, `monthly_expense_total` RPC — complete

## Suggested Next Command

After plan approval: `/speckit-tasks` to generate `tasks.md`.
