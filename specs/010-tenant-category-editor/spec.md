# Feature Specification: Tenant Category Editor

**Feature Branch**: `010-tenant-category-editor`

**Created**: 2026-06-20

**Status**: Draft

**Input**: Web UI to create, edit, and delete level-1 and level-2 expense categories per personal or group/room ledger. On delete, transfer logged expenses to another category. Bottom-tab navigation. Each tenant has its own taxonomy (lazy-copied from global default). Bot uses tenant taxonomy for categorization.

## Clarifications

### Session 2026-06-20

- Q: Bot integration when categories are customized? → A: **Full sync** — bot uses tenant taxonomy for LLM prompts, new expenses, reply-edits, and confirmations.
- Q: What can users edit? → A: **Full CRUD** — add, rename, reorder, delete L1 and L2 categories with user-defined names.
- Q: Delete + transfer behavior? → A: On any deletion, user picks **any other L1 or L2** category in the same tenant as the transfer target.
- Q: Navigation pattern? → A: **Bottom tab bar** — Expenses | Categories (shared tenant switcher).
- Q: Default copy timing? → A: **Lazy on first Categories page visit** — copy global taxonomy when user opens Categories for that tenant.

## Out of Scope (this feature)

- Level-3 categories (taxonomy remains max depth 2)
- Editing expenses from the web (remains bot reply-edit flow)
- Per-category budgets or rollup charts
- Localized category names (custom names are Japanese `name_ja` only; UI chrome stays ja/en/zh)
- Category merge/split wizards beyond delete-and-transfer
- Admin/global taxonomy editing from web (global seed remains migration/YAML only)
- Audit log of who changed group taxonomy (deferred)
- Real-time push sync to other members' open browser tabs

## User Scenarios & Testing

### User Story 1 - View and initialize tenant categories (Priority: P1)

A signed-in user opens the **Categories** tab for their personal ledger. On first visit, the system copies the global default taxonomy into a personal copy. The user sees an L1 → L2 tree matching the bot's default household categories.

**Why this priority**: Without a tenant taxonomy instance, no edits are possible and bot sync cannot begin.

**Independent Test**: Sign in, open Categories for personal tenant, confirm default tree appears and a second visit does not duplicate nodes.

**Acceptance Scenarios**:

1. **Given** a user with no prior tenant taxonomy, **When** they open Categories for personal ledger, **Then** L1/L2 nodes are created as a copy of the global template and displayed in sort order.
2. **Given** taxonomy already exists for the tenant, **When** the user opens Categories again, **Then** the same nodes are shown (no duplicate copy).
3. **Given** a user switches tenant in the tab bar context, **When** Categories loads, **Then** the tree reflects that tenant's taxonomy (initializing if needed).

---

### User Story 2 - Create and edit categories (Priority: P1)

A user adds a new L2 under an L1, renames an L1 or L2, or reorders siblings. Changes persist and appear on the next page load.

**Why this priority**: Core CRUD value of the feature.

**Independent Test**: Add L2 "ペットフード", rename L1 "食費" → "食費・飲料", reorder two L2 items, reload and verify.

**Acceptance Scenarios**:

1. **Given** an existing L1, **When** the user adds a new L2 with a name, **Then** it appears under that L1 with a generated stable `code`.
2. **Given** an existing L1 or L2, **When** the user edits the name, **Then** the new name is saved and shown in the category tree.
3. **Given** multiple L1 or L2 siblings, **When** the user changes sort order, **Then** order persists across reloads.
4. **Given** a user adds a new top-level L1, **When** saved, **Then** it appears in the tree and is available for bot categorization after bot cache refresh.

---

### User Story 3 - Delete with expense transfer (Priority: P1)

A user deletes an L1 or L2 that has logged expenses. The system requires choosing a transfer target among **all other** L1 or L2 categories in the same tenant before completing deletion.

**Why this priority**: Prevents orphaned expenses and FK violations; explicit user control over remapping.

**Independent Test**: Log expense in category A via bot, delete A on web, transfer to B, confirm expense shows category B in dashboard and bot.

**Acceptance Scenarios**:

1. **Given** an L2 with expenses, **When** the user deletes it, **Then** they must select another L1 or L2 (not the one being deleted) and all affected expenses are remapped before the node is removed.
2. **Given** an L1 with expenses (assigned at L1 or via child L2), **When** the user deletes it, **Then** they select a transfer target and all affected expenses under that L1 subtree are remapped; child L2 nodes are removed with the L1.
3. **Given** a category with zero expenses, **When** the user deletes it, **Then** deletion completes without a transfer step.
4. **Given** only one L1 remains in the tenant, **When** the user attempts to delete it, **Then** deletion is blocked with a clear message (tenant must retain at least one category).

---

### User Story 4 - Group taxonomy editable by any member (Priority: P1)

A group member opens Categories while the group tenant is selected and edits the shared taxonomy. Another member's bot categorization and dashboard use the updated tree.

**Why this priority**: Group ledger is a first-class tenant; shared taxonomy must be collaborative.

**Independent Test**: Two members in same group; member A renames a category; member B logs new expense via bot; confirm new name in confirmation and dashboard.

**Acceptance Scenarios**:

1. **Given** user A is in group G per `tenant_chat_members`, **When** A edits group G taxonomy, **Then** changes persist under `tenant_type=group`, `tenant_id=G`.
2. **Given** user B is in the same group, **When** B opens Categories for G, **Then** B sees A's changes and may also edit.
3. **Given** user C is not in group G, **When** C attempts API write to G taxonomy, **Then** the request is denied by RLS.

---

### User Story 5 - Bot uses tenant taxonomy (Priority: P1)

When a user logs an expense via the LINE bot (personal or group), categorization LLM prompts, validation, confirmation display, and reply-edits use that tenant's taxonomy—not the global template—once a tenant copy exists.

**Why this priority**: Full-sync requirement; without this, web edits would not affect bot behavior.

**Independent Test**: Customize personal taxonomy on web, log expense via bot in 1:1, confirm LLM options only include tenant codes.

**Acceptance Scenarios**:

1. **Given** a tenant with customized taxonomy, **When** a new expense is categorized, **Then** guessed/alternative codes are validated against tenant nodes only.
2. **Given** a tenant that has never opened Categories (no tenant copy), **When** the bot categorizes, **Then** it uses the global template (current behavior).
3. **Given** a renamed L2, **When** the bot sends a confirmation, **Then** the displayed category path uses the updated `name_ja`.

---

### User Story 6 - Bottom tab navigation (Priority: P2)

Signed-in users navigate between **Expenses** and **Categories** via a persistent bottom tab bar. Tenant selection is consistent across tabs.

**Why this priority**: Required navigation pattern; secondary to data correctness.

**Independent Test**: On mobile viewport, tap both tabs; tenant switcher selection persists.

**Acceptance Scenarios**:

1. **Given** a signed-in user on `/dashboard`, **When** they tap Categories, **Then** they land on `/categories` with the same selected tenant.
2. **Given** a user on `/categories`, **When** they tap Expenses, **Then** they return to `/dashboard` without re-authenticating.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST store per-tenant category trees for `tenant_type` ∈ {`user`, `group`, `room`} and matching `tenant_id`.
- **FR-002**: System MUST lazy-initialize tenant taxonomy on first Categories page load by copying all global template `category_nodes` (where `tenant_type` IS NULL) into tenant-scoped rows with new UUIDs, preserving `code`, hierarchy, `sort_order`, and `name_ja`.
- **FR-003**: On lazy init, system MUST remap existing expenses for that tenant from global template category IDs to tenant copy IDs by matching `code`.
- **FR-004**: Users MUST be able to create, rename, reorder, and delete L1 and L2 categories for tenants they can access.
- **FR-005**: Deleting a category with expenses MUST require selecting a transfer target that is any other L1 or L2 in the same tenant; remapping MUST update `category_node_id`, `assigned_level`, `category_l1_id`, and `category_l2_id` on affected expenses.
- **FR-006**: Transfer to an L1 target MUST set `assigned_level=1` and clear `category_l2_id`; transfer to an L2 target MUST set `assigned_level=2` with correct L1/L2 denormalized IDs.
- **FR-007**: System MUST prevent deletion of the last remaining L1 in a tenant taxonomy.
- **FR-008**: System MUST retain a non-deletable `unknown` (不明) L1 per tenant (copied from template; cannot be deleted).
- **FR-009**: Any member of a group/room per `tenant_chat_members` MUST have write access to that tenant's taxonomy; personal taxonomy writable only by owning `line_user_id`.
- **FR-010**: Bot MUST resolve taxonomy by tenant: tenant copy if exists, else global template.
- **FR-011**: Web dashboard expense list MUST display category names from tenant nodes after customization.
- **FR-012**: Bottom tab bar MUST link `/dashboard` (Expenses) and `/categories` (Categories) for authenticated users.
- **FR-013**: New user-created categories MUST receive auto-generated unique `code` values scoped per tenant (e.g. `custom.<short-id>`).

### Edge Cases

- Concurrent edits by two group members: last-write-wins on row updates; document in UI that refresh may be needed.
- Deleting L1 that still has L2 children without expenses: child L2 nodes are deleted with L1 after transfer step (only expenses force transfer).
- Bot mid-flight during taxonomy copy: bot continues using global template until tenant rows exist; after copy, next message uses tenant taxonomy.
- Category code collisions on custom add: server rejects duplicate codes within tenant.
- Expense assigned to `unknown`: transfer picker includes all other categories; `unknown` remains as fallback for LLM.

## Key Entities

- **Global template category** (`category_nodes` with NULL tenant): seeded household taxonomy; read-only reference for lazy copy.
- **Tenant category** (`category_nodes` with `tenant_type` + `tenant_id`): editable L1/L2 tree per ledger.
- **Expense** (existing): FK references to tenant category UUIDs after init/remap.
- **Tenant membership** (`tenant_chat_members`): gates group/room taxonomy write access.

## Success Criteria

- **SC-001**: User can complete first-time category setup (lazy copy) and add a custom L2 in under 60 seconds on mobile.
- **SC-002**: After delete-and-transfer, 100% of affected expenses show the chosen category in dashboard and bot confirmation.
- **SC-003**: Bot categorization after customization never references codes absent from tenant taxonomy.
- **SC-004**: Unauthorized cross-tenant taxonomy writes are blocked by RLS in integration tests.
