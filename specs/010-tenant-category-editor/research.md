# Research: Tenant Category Editor

**Feature**: 010-tenant-category-editor

## Decision 1: Single table vs separate tenant table

**Decision**: Extend existing `category_nodes` with nullable `tenant_type` / `tenant_id`.

**Rationale**: Expenses already FK to `category_nodes`. A separate table would require polymorphic FKs or expense schema changes. Nullable tenant columns keep template rows as the migration seed and allow tenant rows to participate in the same joins and view.

**Alternatives considered**:
- `tenant_category_nodes` child table — cleaner separation but requires expense FK migration.
- JSON blob per tenant — poor FK integrity and query ergonomics.

## Decision 2: UUID strategy on copy

**Decision**: Generate new `gen_random_uuid()` for tenant copies; remap expenses by matching `code`.

**Rationale**: Template uses deterministic uuid5 IDs shared across all tenants today. Tenant copies must be independent so edits do not cross tenants. `code` is the stable semantic key during copy.

**Alternatives considered**:
- Reuse template UUIDs per tenant — would break global uniqueness on PK.
- Composite PK (tenant + code) — larger expense migration.

## Decision 3: Lazy init trigger

**Decision**: Server-side `ensure_tenant_taxonomy()` on Categories page load (and optionally bot first use).

**Rationale**: User chose lazy on first Categories visit. Avoids copying taxonomy for inactive tenants. Bot can continue using global template until copy exists; first web visit remaps historical expenses.

**Alternatives considered**:
- Eager on sign-up — unnecessary DB writes.
- On first expense — user explicitly chose web visit.

## Decision 4: Bot taxonomy loading

**Decision**: Query Supabase for tenant rows at categorization time (with in-memory LRU cache keyed by tenant).

**Rationale**: Full-sync requirement. YAML file cache is insufficient once tenants customize. Bot already has Supabase service role access.

**Alternatives considered**:
- Continue YAML-only — incompatible with per-tenant names/codes.
- Webhook invalidation — over-engineered for MVP.

## Decision 5: Delete transfer UX

**Decision**: Modal with flat list grouped by L1 showing all other L1 and L2 targets.

**Rationale**: User can pick any L1 or L2. Flat picker is simpler than cascading two-step on mobile.

## Decision 6: Navigation shell

**Decision**: Shared `AppShell` layout with bottom `TabBar` for `/dashboard` and `/categories`; tenant switcher in page header on both routes.

**Rationale**: Matches option A; mobile-first LINE users.

## Decision 7: Write API surface

**Decision**: Next.js Route Handlers (`/api/categories/*`) using Supabase server client + RLS; mutations as explicit endpoints (init, create, update, reorder, delete).

**Rationale**: Consistent with existing auth routes; complex delete-and-transfer logic in one transactional server route. Alternative: direct Supabase client writes — harder to orchestrate multi-row transfer atomically from browser.

## Decision 8: Custom category codes

**Decision**: Server generates `custom.<8-char-hex>` on create; not user-editable.

**Rationale**: LLM prompts need stable codes; users only edit `name_ja`.

## Open questions (deferred)

- Optimistic UI for group concurrent edits — last-write-wins for MVP.
- "Reset to default" action — not requested; add later if needed.
