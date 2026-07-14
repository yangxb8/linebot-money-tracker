# Data Model: Item-Level Category Memory

**Feature**: 018-item-category-memory

## ERD (conceptual)

```text
category_merchant_memory ── tenant + merchant_key → category   (013, text path)

category_item_memory ── tenant + memory_kind + merchant_key? + item_key → category
         │
         ├── store_item: merchant_key NOT NULL
         └── item_only:  merchant_key NULL

expenses
  category_source: memory | item_memory | llm
  metadata.store_name (014) —— receipt lineage for backfill / reply-edit isolation
```

## Entity: category_item_memory (new)

Per-tenant learned mapping from item identity to taxonomy category.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | `gen_random_uuid()` |
| tenant_type | text NOT NULL | `user` \| `group` \| `room` |
| tenant_id | text NOT NULL | |
| memory_kind | text NOT NULL | `store_item` \| `item_only` |
| merchant_key | text NULL | Required when `memory_kind = store_item`; NULL when `item_only` |
| item_key | text NOT NULL | Normalized product key |
| display_merchant | text NULL | Latest store display string (store_item) |
| sample_description | text NULL | Last raw/cleaned description |
| category_code | text NOT NULL | Tenant-valid taxonomy code |
| weight | numeric(6,2) NOT NULL DEFAULT 0 | Skip LLM when ≥ 1.0 |
| hit_count | int NOT NULL DEFAULT 0 | |
| last_source | text NOT NULL | `llm` \| `user_correction` \| `silent_confirm` \| `backfill` |
| last_corrected_by | text NULL | LINE user id on correction |
| created_at | timestamptz NOT NULL DEFAULT now() | |
| updated_at | timestamptz NOT NULL DEFAULT now() | |

**Constraints**:

```sql
CHECK (tenant_type IN ('user', 'group', 'room'))
CHECK (memory_kind IN ('store_item', 'item_only'))
CHECK (weight >= 0)
CHECK (last_source IN ('llm', 'user_correction', 'silent_confirm', 'backfill'))
CHECK (
  (memory_kind = 'store_item' AND merchant_key IS NOT NULL)
  OR (memory_kind = 'item_only' AND merchant_key IS NULL)
)
```

**Uniqueness** (partial indexes — Postgres NULL-safe):

```sql
CREATE UNIQUE INDEX uq_category_item_memory_store_item
  ON category_item_memory (tenant_type, tenant_id, merchant_key, item_key)
  WHERE memory_kind = 'store_item';

CREATE UNIQUE INDEX uq_category_item_memory_item_only
  ON category_item_memory (tenant_type, tenant_id, item_key)
  WHERE memory_kind = 'item_only';
```

**Lookup indexes**:

```sql
CREATE INDEX idx_category_item_memory_store_lookup
  ON category_item_memory (tenant_type, tenant_id, merchant_key, item_key)
  WHERE memory_kind = 'store_item';

CREATE INDEX idx_category_item_memory_item_lookup
  ON category_item_memory (tenant_type, tenant_id, item_key)
  WHERE memory_kind = 'item_only';
```

**RLS**: Not enabled in v1 (bot service role only) — same pattern as `category_merchant_memory`.

### Weight / write matrix

| Event | store_item | item_only |
| ----- | ---------- | --------- |
| LLM seed | `weight += 0.25`, `last_source=llm` | **no write** |
| Silent confirm | `weight += 0.5`, `last_source=silent_confirm` | **no write** |
| User correction | `weight = 1.0`, set category | `weight = 1.0`, set category |
| Backfill | capped ≤ 1.0, `last_source=backfill`, last expense wins | **no write** |
| Memory hit (read) | optional `hit_count++` | optional `hit_count++` |

## Entity: expenses (delta)

Widen `category_source` check:

```sql
CHECK (
  category_source IS NULL
  OR category_source IN ('memory', 'item_memory', 'llm')
)
```

| Value | Meaning |
| ----- | ------- |
| `memory` | Merchant-only memory hit (text path) |
| `item_memory` | store_item or item_only hit (receipt path) |
| `llm` | Category LLM (may include soft prior) |

No new expense columns required for item_key (derive at runtime / backfill); optional future denormalization deferred.

## Entity: Item key (derived, not stored on expense)

See [contracts/item-normalize.md](./contracts/item-normalize.md).

## Relationships

| From | To | Cardinality |
| ---- | -- | ----------- |
| Tenant | category_item_memory | 1:N |
| category_item_memory.category_code | category_nodes.code | logical (validated in app via `resolve_code`) |
| expense (receipt) | store_item row | N:1 via derived keys at runtime |

## Migration notes

- Additive only; do not migrate or delete merchant memory rows.
- Existing merchant high-weight rows for home centers remain for **text** path; receipt path ignores them for hard-skip (soft prior only).
