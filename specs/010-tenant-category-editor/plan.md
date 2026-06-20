# Implementation Plan: Tenant Category Editor

**Branch**: `010-tenant-category-editor` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)

**Input**: Per-tenant editable L1–L2 category CRUD on web with delete-and-transfer, side-drawer navigation, lazy default copy, and full bot taxonomy sync.

## Summary

Extend `category_nodes` with tenant scope so each personal and group/room ledger owns an editable category tree. On first visit to `/categories`, copy the global template, remap existing expenses by `code`, and expose CRUD in a mobile-first UI with a side drawer for navigation. Bot loads taxonomy per `TenantContext` from Supabase instead of the static YAML cache when tenant rows exist. Delete requires transferring expenses to any other L1 or L2 in the same tenant.

## Technical Context

**Language/Version**: TypeScript / Node 20+ (Next.js 15 App Router); Python 3.11+ bot

**Primary Dependencies**: Next.js, `@supabase/supabase-js`, `@supabase/ssr`, existing bot Supabase client

**Storage**: Supabase Postgres — migration on `category_nodes`; new RLS write policies; optional RPC `ensure_tenant_taxonomy` / `delete_category_with_transfer`

**Testing**: pytest for bot taxonomy resolution + delete remap; Vitest for web API handlers; SQL/RLS integration tests; manual mobile checklist

**Target Platform**: Vercel (`web/`) + LINE bot (Cloud Run) + Supabase hosted Postgres

**Performance Goals**: Category tree load ≤1s p95; lazy init ≤3s for ~40 nodes; bot taxonomy cache hit avoids DB round-trip per message

**Constraints**:
- Service role key stays server-side only
- Max category depth 2
- RLS enforces tenant isolation (extends 009 patterns)
- `unknown` category non-deletable per tenant

**Scale/Scope**: Same as 009 — household users, tens of categories per tenant, low concurrent editors

## Constitution Check

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Shared taxonomy service in bot; web `lib/categories/` module; SQL in migrations |
| Test-First Delivery | Tests for lazy copy remap, delete-transfer, RLS deny cross-tenant, bot `resolve_code` per tenant |
| User Experience Consistency | ja/en/zh UI strings; Japanese category names; mobile side drawer nav |
| Performance & Reliability | Transactional init/delete; LRU taxonomy cache in bot |
| Observability | Structured logs on init/delete routes; no PII in client logs |

**Gate**: PASS

## Architecture

```text
┌──────────────────┐     side drawer      ┌─────────────────────────┐
│  /dashboard      │ ◄──────────────────► │  /categories            │
│  ExpenseList     │   (hamburger menu)   │  CategoryTree + CRUD    │
└────────┬─────────┘                      └───────────┬─────────────┘
         │                                            │
         │  Supabase JS (authenticated)               │  /api/categories/*
         ▼                                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Supabase Postgres                                                  │
│  category_nodes (template + tenant rows)                            │
│  expenses (FK → tenant category IDs)                                │
│  RLS: read/write by tenant membership                               │
└─────────────────────────────────────────────────────────────────────┘
         ▲
         │ service role + tenant-scoped taxonomy query
┌────────┴────────┐
│  LINE bot       │  categorize / reply-edit use tenant taxonomy
└─────────────────┘
```

### Category init flow

1. User opens `/categories?tenant=...` (tenant from switcher state).
2. `GET /api/categories?tenant_type&tenant_id` calls `ensure_tenant_taxonomy` RPC.
3. If no tenant rows: copy template → remap expenses → return tree.
4. UI renders L1 groups with nested L2.

### Delete flow

1. User taps delete on L1 or L2.
2. `GET /api/categories/:id/usage` returns expense count (optional prefetch).
3. If count > 0: show transfer picker (all other L1/L2).
4. `POST /api/categories/:id/delete` with `{ transfer_to_id }` runs transactional remap + delete.

### Bot sync flow

1. `MessageContext` / `TenantContext` passed to `categorize.py`.
2. `load_category_taxonomy(tenant_type, tenant_id)` queries DB (cached).
3. Prompt lists tenant codes; validation uses tenant map; `resolve_code` returns tenant node IDs.

## Project Structure

### Documentation

```text
specs/010-tenant-category-editor/
├── spec.md
├── plan.md
├── data-model.md
├── research.md
├── quickstart.md
└── contracts/
    ├── supabase-schema-delta.md
    └── categories-api.md
```

### Source Code

```text
supabase/migrations/
  20260620140000_tenant_category_nodes.sql   # tenant columns, RLS, RPCs

web/src/
  app/
    (app)/                                    # route group with AppShell
      layout.tsx                              # header + SideDrawer
      dashboard/page.tsx                      # moved from app/dashboard
      categories/page.tsx
    api/categories/
      route.ts                                # GET tree, POST create
      [id]/route.ts                           # PATCH rename/reorder
      [id]/delete/route.ts                    # POST delete+transfer
      init/route.ts                           # optional explicit init
  components/
    SideDrawer.tsx
    AppHeader.tsx                             # hamburger + tenant switcher
    TenantSwitcher.tsx                        # reused
    categories/
      CategoryTree.tsx
      CategoryEditor.tsx
      DeleteCategoryDialog.tsx
  lib/categories/
    types.ts
    client.ts                                 # fetch helpers

services/
  category_taxonomy.py                        # tenant-aware load + DB fetch
  categorize.py                               # pass tenant into taxonomy
  expense_repository.py                       # tenant on resolve_code

tests/
  test_tenant_category_taxonomy.py
  test_category_delete_transfer.py
```

## Implementation Phases

### Phase 1 — Schema & RLS (blocking)

1. Migration: add `tenant_type`, `tenant_id`, `created_at` to `category_nodes`.
2. Replace global `UNIQUE(code)` with partial uniques (template vs tenant).
3. RLS: SELECT template + own/member tenant rows; INSERT/UPDATE/DELETE tenant rows only.
4. RPC `ensure_tenant_taxonomy(p_tenant_type, p_tenant_id)` — idempotent copy + expense remap.
5. RPC `delete_category_with_transfer(p_node_id, p_transfer_to_id)` — transactional delete.

### Phase 2 — Bot taxonomy sync

1. Refactor `load_category_taxonomy(tenant_type, tenant_id)` to query Supabase when configured.
2. Thread `TenantContext` through `categorize.py`, `reply_edit`, `map_category_from_text`.
3. LRU cache per tenant; fall back to YAML template when no tenant rows.
4. Unit tests with mocked Supabase rows.

### Phase 3 — Web navigation shell

1. Introduce `(app)` route group with `AppShell` + `SideDrawer` (Expenses | Categories links).
2. Add `AppHeader` with hamburger trigger, page title, and shared tenant switcher.
3. Move dashboard under `(app)/dashboard`; preserve auth middleware paths.
4. Share tenant selection via URL search param `?t=group:abc123` or React context + localStorage.
5. Drawer closes on nav item tap, backdrop tap, or swipe; trap focus while open (a11y).

### Phase 4 — Categories UI

1. `/categories` page: tree view, add L1/L2, inline rename, reorder (up/down buttons).
2. Delete flow with transfer modal when expenses exist.
3. i18n strings in `messages.ts`.
4. Loading/error/empty states.

### Phase 5 — API routes

1. `GET /api/categories` — ensure init + return tree.
2. `POST /api/categories` — create L1/L2.
3. `PATCH /api/categories/[id]` — rename, reorder.
4. `POST /api/categories/[id]/delete` — delete with optional transfer body.
5. Server-side tenant authorization mirrors RLS.

### Phase 6 — Verification

1. RLS SQL tests: cross-tenant write denied.
2. E2E manual: customize → bot log → dashboard shows new name.
3. Delete transfer: expense count zero on deleted node after remap.

## Risks & Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Expense remap misses edge FK combinations | Integration test all `category_*_id` columns; use RPC in single transaction |
| Bot/cache stale after web edit | Short TTL cache (60s) or cache clear on taxonomy version timestamp |
| Group concurrent edits | Last-write-wins; show toast to refresh |
| Large expense count on L1 delete | Batch UPDATE in RPC; show progress for >500 rows (unlikely MVP) |

## Dependencies

- **009-expense-web-dashboard**: auth, tenant switcher, RLS `current_line_user_id()` — complete
- **006-group-expenses**: `tenant_type` / `tenant_id` on expenses — complete
- **004-supabase-expense-storage**: `category_nodes` base schema — complete

## Suggested Next Command

After plan approval: `/speckit-tasks` to generate `tasks.md`, or proceed directly to Phase 1 migration.
