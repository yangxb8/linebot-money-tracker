# Research: Tenant Category Memory

**Feature**: 013-tenant-category-memory

## Decision 1: Per-tenant memory table (not global)

**Decision**: Store mappings in `category_merchant_memory` keyed by `(tenant_type, tenant_id, merchant_key)`.

**Rationale**: Tenants customize taxonomy (010); same merchant may map to different categories per household or group. User explicitly reverted cross-tenant sharing.

**Alternatives considered**:
- **Global memory** — breaks tenant-specific category trees and group vs personal isolation.
- **Per-user within group** — spec says easiest implementation; last writer wins at tenant level.

## Decision 2: Merchant extraction via dedicated LLM call (v1)

**Decision**: New `extract_merchant_name(description, amount, currency)` under `llm_operation_scope('merchant_extract')` before category lookup. Returns `merchant_name | null`.

**Rationale**: User chose LLM over rules-only extraction. Dedicated call keeps `assist` parse schema stable and is testable in isolation.

**Alternatives considered**:
- **Merge into assist/receipt parse JSON** — fewer tokens/calls but requires prompt/schema changes across text, OCR, and vision paths; defer as optimization after v1.
- **Rules-only extraction** — rejected by user.

**Prompt contract**: Return JSON `{"merchant_name": string | null}`. Null when generic or unidentifiable.

## Decision 3: Normalization pipeline (rules + YAML aliases)

**Decision**: After LLM extraction, run deterministic `normalize_merchant_key()`:

1. NFKC unicode normalize
2. Strip branch suffixes (`店`, `支店`, `駅前`, trailing digits)
3. Lookup `data/merchant_aliases_ja.yaml` (longest match / exact variant)
4. Emit lowercase ASCII `merchant_key` (snake_case)

**Rationale**: Matches user choice for first normalization option; aliases collapse セブン / 7-ELEVEN / ｾﾌﾞﾝ to one key.

**Generic denylist** (skip memory read/write): `食費`, `買い物`, `支出`, `payment`, `expense`, `不明`, `misc`, tokens `< 2` chars after normalize.

## Decision 4: Weight model and skip threshold

**Decision**:

| Event | Weight change |
| ----- | ------------- |
| Category LLM guess persisted (memory miss or weight < 1.0) | `+0.25`, `last_source=llm` |
| Silent confirm | `+0.5`, `last_source=silent_confirm` |
| Explicit category correction (reply-edit) | Set `weight=1.0`, `last_source=user_correction` |
| Backfill | Set up to `1.0` from historical consistency |

**Skip category LLM** when lookup returns `weight >= 1.0` and `resolve_code(category_code, tenant)` is valid (not forced unknown fallback).

**Rationale**: User-specified numbers. LLM alone (4×0.25) never reaches skip; needs correction or silent confirms.

## Decision 5: Silent confirm trigger

**Decision**: Apply `+0.5` silent confirm when **a new expense is persisted** for extractable `merchant_key` and the **most recent prior expense** for the same `(tenant, merchant_key)`:

- Has `category_guess_code` equal to its final stored category code (no category change), AND
- Has no `reply_edit_audit` row with category change for that expense

If no prior expense exists, no silent confirm on first log (only LLM `+0.25`).

**Rationale**: Users do not tap “confirm”; not replying to confirmation then logging again is the natural acceptance signal (US3). Checking prior expense avoids needing a new confirmation lifecycle.

**Alternatives considered**:
- **On reply-edit only** — misses users who never reply-edit.
- **Immediate after insert** — no prior expense to compare on first log.

## Decision 6: Memory hit UX

**Decision**: Memory guesses use same confirmation copy (`カテゴリ（推測）`); **empty alternatives** on memory hit (weight ≥ 1.0).

**Rationale**: User requested no label change; empty alts reduce noise when confidence is high.

## Decision 7: Expense provenance columns

**Decision**: Add nullable `category_guess_code text` and `category_source text` (`memory` | `llm`) on `expenses`. Populate at insert time.

**Rationale**: FR-016/FR-017 analytics without joining audit tables.

## Decision 8: Backfill strategy

**Decision**: SQL migration includes idempotent `backfill_category_merchant_memory()`:

1. Scan non-deleted `expenses` ordered by `created_at`
2. For each row: resolve `category_code` from stored category FKs
3. Merchant key: **YAML alias + heuristic** on description (first meaningful token / alias match) — **no LLM** in backfill to avoid cost and batch complexity
4. Upsert per `(tenant, merchant_key)`; last expense wins on category conflict
5. Weight = `min(1.0, 0.25 + 0.5 * (count_same_category - 1))` for expenses sharing tenant+merchant+category

**Rationale**: User wants backfill; LLM on full history is expensive. Heuristic + YAML covers major chains; live path uses LLM going forward.

**Re-run**: `ON CONFLICT` upsert safe; backfill function callable from migration and CLI script.

## Decision 9: Repository module layout

**Decision**:

- `services/merchant_normalize.py` — YAML load, denylist, `normalize_merchant_key`, alias lookup
- `services/merchant_extract.py` — LLM extract + validate JSON schema
- `services/category_memory.py` — lookup, upsert, weight deltas, silent confirm helper
- `services/categorize.py` — add `classify_expense_with_memory(item, gemini, tenant)` orchestrating extract → lookup → classify_expense or memory short-circuit

**Rationale**: Single responsibility; `message_handler` calls one entry point.

## Decision 10: Reply-edit learning hook

**Decision**: After successful category change in `reply_edit.apply_edit_intent`, call `category_memory.record_user_correction(tenant, description, category_code, gemini)`.

After any successful edit where category unchanged, call `category_memory.maybe_silent_confirm` only via new-expense path (Decision 5), not on amount-only edits of same message (avoid double-count). Amount-only edits on same confirmation do not strengthen memory.

**Rationale**: Explicit correction is highest signal; silent confirm tied to repeat logging.

## Decision 11: No web UI / service-role only writes

**Decision**: Bot uses service role; table has no RLS policies in v1. No web routes.

**Rationale**: User confirmed no web UI.

## Decision 12: Analytics RPC

**Decision**: `get_category_accuracy_stats(p_tenant_type, p_tenant_id, p_days int default 30)` returns:

```json
{
  "total_expenses": 120,
  "pct_guess_unchanged": 0.72,
  "pct_guess_unknown": 0.08
}
```

`pct_guess_unchanged` = share where `category_guess_code` equals final category code and no category audit edit. `pct_guess_unknown` = share where `category_guess_code = 'unknown'`.

**Rationale**: FR-017; supports SC-001/SC-002 measurement.

## Decision 13: Feature 014 boundary

**Decision**: 013 does not add `store_name` to parse pipeline. Merchant LLM uses `description` only until 014 ships.

**Rationale**: User deferred receipt store to separate spec.
