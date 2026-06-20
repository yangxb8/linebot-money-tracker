# Data Model: Tenant Category Editor

**Feature**: 010-tenant-category-editor

## ERD (conceptual)

```text
category_nodes (global template, tenant_type IS NULL)
    │
    │ lazy copy on first /categories visit
    ▼
category_nodes (tenant-scoped rows)
    │
    ├──< expenses (tenant_type, tenant_id) ── FK category_*_id
    │
    └── tenant_chats / tenant_chat_members (access control)
```

## Entity: category_nodes (extended)

Existing table gains tenant scope. Global template rows remain the migration seed (`tenant_type` and `tenant_id` both NULL). Tenant rows reference the same table with populated tenant keys.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | `gen_random_uuid()` for tenant rows; template keeps uuid5 seed IDs |
| code | text NOT NULL | Stable slug; unique per tenant scope |
| name_ja | text NOT NULL | Display label (user-editable) |
| level | smallint | 1 or 2 only |
| parent_id | uuid FK → category_nodes | NULL for L1 |
| sort_order | int | Sibling ordering |
| tenant_type | text NULL | `user` / `group` / `room`; NULL = global template |
| tenant_id | text NULL | LINE userId or chat ID; NULL = global template |
| created_at | timestamptz | Optional audit; default now() |

**Constraints**:

- `(tenant_type IS NULL) = (tenant_id IS NULL)` — both set or both null
- Template: `UNIQUE (code) WHERE tenant_type IS NULL`
- Tenant: `UNIQUE (tenant_type, tenant_id, code)`
- Level/parent checks unchanged
- Max depth 2 (no L3)

**Special rows per tenant**: `unknown` L1 copied from template; non-deletable.

## Entity: tenant_taxonomy_initialized (optional marker)

Lightweight alternative to inferring init from row count:

| Column | Type | Notes |
| ------ | ---- | ----- |
| tenant_type | text PK | |
| tenant_id | text PK | |
| initialized_at | timestamptz | Set on successful lazy copy |

*Decision*: Prefer detecting init via `EXISTS (SELECT 1 FROM category_nodes WHERE tenant_type = ? AND tenant_id = ?)` to avoid extra table unless copy idempotency needs explicit locking.

## Lazy copy algorithm

1. `SELECT` global template nodes (`tenant_type IS NULL`) ordered by level, sort_order.
2. If tenant already has rows, return existing tree.
3. In a transaction:
   - Insert L1 nodes with new UUIDs; build `old_id → new_id` map keyed by `code`.
   - Insert L2 nodes with `parent_id` mapped via parent code.
   - `UPDATE expenses` for tenant: join old template IDs to new IDs via `code` on `category_node_id`, `category_l1_id`, `category_l2_id`.
4. Commit.

## Delete + transfer algorithm

Input: `node_id` to delete, `target_id` (another L1 or L2 in same tenant).

1. Validate target ≠ source; same tenant; target exists.
2. Resolve `target` level → compute new `assigned_level`, `category_node_id`, `category_l1_id`, `category_l2_id`.
3. `UPDATE expenses` WHERE tenant matches AND (
   - deleting L2: `category_node_id = node_id` OR `category_l2_id = node_id`
   - deleting L1: `category_l1_id = node_id` OR any child L2 under node
   ).
4. If deleting L1: delete child L2 rows, then L1.
5. If deleting L2: delete L2 row.

## Bot taxonomy resolution

```text
load_category_taxonomy(tenant_type, tenant_id):
  rows = SELECT * FROM category_nodes WHERE tenant_type = ? AND tenant_id = ?
  if rows.empty:
    return load_global_template()  # current YAML/DB template
  return build_tree(rows)
```

Cache key: `(tenant_type, tenant_id)` with TTL or invalidation on write (bot reload per request acceptable for MVP).

## RLS policies (category_nodes)

| Operation | Personal (`user`) | Group/Room |
| --------- | ----------------- | ---------- |
| SELECT template | all authenticated | all authenticated |
| SELECT tenant | owner or member | member via `tenant_chat_members` |
| INSERT/UPDATE/DELETE tenant | `tenant_id = current_line_user_id()` | member of tenant |

Template rows: SELECT only, no writes from `authenticated`.

## Application state: Categories page

| State | Description |
| ----- | ----------- |
| loading | Fetching or initializing taxonomy |
| ready | Tree displayed |
| editing | Inline/modal create or rename |
| delete_confirm | Transfer picker shown when expenses exist |
| error | RLS or validation failure |

## Indexes

- `(tenant_type, tenant_id, level, sort_order)` — tree load
- `(tenant_type, tenant_id, code)` — unique lookup (covered by unique constraint)

## View: v_expenses_enriched

No schema change required; joins `category_nodes` by expense FK IDs. After tenant remap, names resolve from tenant rows automatically.
