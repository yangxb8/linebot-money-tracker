# Data Model: Tenant Category Memory

**Feature**: 013-tenant-category-memory

## ERD (conceptual)

```text
category_nodes (tenant-scoped, 010)
    │
    └──< expenses >── tenant (type, id)
              │              category_guess_code, category_source (new)
              │
category_merchant_memory ── tenant (type, id) + merchant_key → category_code
```

## Entity: category_merchant_memory

Per-tenant learned mapping from normalized merchant key to taxonomy category code.

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid PK | `gen_random_uuid()` |
| tenant_type | text NOT NULL | `user` \| `group` \| `room` |
| tenant_id | text NOT NULL | LINE userId or chat ID |
| merchant_key | text NOT NULL | Normalized ASCII key, e.g. `seven_eleven` |
| display_merchant | text | Latest raw LLM extraction for logs/UI debug |
| category_code | text NOT NULL | Taxonomy code valid for tenant via `resolve_code` |
| weight | numeric(6,2) NOT NULL DEFAULT 0 | Confidence; skip LLM when ≥ 1.0 |
| hit_count | int NOT NULL DEFAULT 0 | Times memory used or updated |
| last_source | text NOT NULL | `llm` \| `user_correction` \| `silent_confirm` \| `backfill` |
| last_corrected_by | text NULL | `line_user_id` on user_correction |
| sample_description | text | Last expense description seen |
| created_at | timestamptz NOT NULL DEFAULT now() | |
| updated_at | timestamptz NOT NULL DEFAULT now() | |

**Constraints**:

```sql
UNIQUE (tenant_type, tenant_id, merchant_key)
CHECK (tenant_type IN ('user', 'group', 'room'))
CHECK (weight >= 0)
CHECK (last_source IN ('llm', 'user_correction', 'silent_confirm', 'backfill'))
```

**Indexes**:

```sql
CREATE INDEX idx_category_merchant_memory_lookup
  ON category_merchant_memory (tenant_type, tenant_id, merchant_key);
```

**RLS**: Disabled in v1 (bot service role only). No web access.

### Weight transitions

| Operation | SQL effect |
| --------- | ---------- |
| LLM seed | `weight = weight + 0.25`, `hit_count++` |
| Silent confirm | `weight = weight + 0.5`, `hit_count++` |
| User correction | `weight = 1.0`, `category_code = $new`, `hit_count++` |
| Memory hit (read) | `hit_count++` optional (implementation: increment on use) |
| Backfill | `weight = LEAST(1.0, computed)`, `last_source=backfill` |

## Entity: expenses (delta)

Add columns to existing `expenses` table:

| Column | Type | Notes |
| ------ | ---- | ----- |
| category_guess_code | text NULL | First assigned code at insert |
| category_source | text NULL | `memory` \| `llm` |

**Constraints**:

```sql
CHECK (category_source IS NULL OR category_source IN ('memory', 'llm'))
```

Existing rows: NULL until backfill not required (analytics only for new expenses post-deploy).

## Static data: merchant_aliases_ja.yaml

Not a DB table. Loaded at bot startup / first use.

```yaml
seven_eleven:
  - セブン-イレブン
  - セブンイレブン
  - 7-ELEVEN
  - 7-11
```

See [appendix-merchant-alias-seed.md](./appendix-merchant-alias-seed.md) for minimum coverage.

## RPC: get_category_accuracy_stats

**Inputs**: `p_tenant_type text`, `p_tenant_id text`, `p_days int default 30`

**Output** (JSON):

| Field | Type | Description |
| ----- | ---- | ----------- |
| total_expenses | int | Non-deleted expenses in window |
| pct_guess_unchanged | numeric | Fraction where guess matched final category without category audit edit |
| pct_guess_unknown | numeric | Fraction where `category_guess_code = 'unknown'` |

**Window**: `expense_date >= (today JST - p_days)`.

## Function: backfill_category_merchant_memory()

Idempotent PL/pgSQL or invoked from Python script `scripts/backfill_category_memory.py`:

1. Iterate expenses `WHERE deleted_at IS NULL` ORDER BY `created_at`
2. Heuristic merchant key from `description` + YAML aliases (Python loader or precomputed keys in script)
3. Upsert memory rows per Decision 8 in research.md

## Relationships

| From | To | Cardinality |
| ---- | -- | ----------- |
| category_merchant_memory | tenant | N:1 |
| category_merchant_memory.category_code | category_nodes.code | logical FK (validated in app) |
| expenses.category_guess_code | category_nodes.code | logical |

## Orphan handling (010 category delete)

When tenant deletes/transfers category, memory rows retaining old `category_code` remain. On lookup, `resolve_code` may map to `unknown` → fall back to category LLM (FR-010). Optional cleanup deferred.
