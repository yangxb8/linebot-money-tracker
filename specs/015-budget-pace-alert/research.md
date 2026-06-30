# Research: Budget Pace Alert in LINE Bot Replies

**Feature**: 015-budget-pace-alert  
**Date**: 2026-06-30

## Decision 1: Reuse `get_budget_summary` RPC from the bot

**Decision**: The Python bot calls existing Supabase RPC `get_budget_summary(p_tenant_type, p_tenant_id, p_budget_month, p_currency)` via service-role client after expense persist or reply-edit apply. No new SQL migrations or materialized counters.

**Rationale**: Feature 012 already computes spent on read with cascade bucket keys in `spent_by_bucket`. The web dashboard uses the same RPC; reusing it keeps bot warnings aligned with `/budget` UI figures.

**Alternatives considered**:
- New `get_budget_pace_for_expense` RPC — rejected; duplicates logic already in summary JSON.
- Client-side spent re-aggregation in Python — rejected; diverges from web and misses fiscal-period rules in SQL.

---

## Decision 2: Port pace math from `web/src/lib/budget/health.ts` to Python

**Decision**: Add `services/budget_pace.py` with `compute_budget_health()` mirroring TypeScript. **Ahead of pace** = `pace_ratio > 1` (equivalent to `spent_pct > time_pct` after day-1 neutral handling).

**Rationale**: Spec FR-004 requires the same definition as web health coloring. A Python port is ~40 lines, testable without a browser, and avoids coupling the bot to Node.

**Alternatives considered**:
- Duplicate formula inline in message handler — rejected; untestable and drifts from web.
- Call web API from bot — rejected; adds auth/latency and couples runtimes.

---

## Decision 3: Multi-level evaluation with lowest-ahead warning (015 clarification)

**Decision**: For each expense path, collect **all defined budget levels** in the cascade (L2 expense → L2 limit if set, parent L1 if set, total if set; L1 expense → L1 if set, total if set). Evaluate pace at each level independently using `spent_by_bucket` totals. Emit **one warning** for the **lowest (most specific) level** where `pace_ratio > 1`. Stop at first match (L2 before L1 before total).

**Rationale**: User clarification (2026-06-30) — check all levels but avoid redundant warnings when L2, L1, and total are all ahead.

**Alternatives considered**:
- Single `resolve_budget_bucket` only — rejected; that picks one spending bucket, not all levels to evaluate.
- Warn on every ahead level — rejected; noisy and contradicts spec clarification.

---

## Decision 4: Hybrid LLM wording with template fallback

**Decision**: Compute facts in Python (category label, limit, spent, remaining, daily allowance, days left, level). Call `gemini.generate_reply()` with a short structured prompt under `llm_operation_scope('budget_pace')` to produce conversational warning text with emoji. On LLM failure or missing API key, fall back to `budget_pace_i18n.py` template strings (ja/en/zh). Never block the confirmation reply (FR-013).

**Rationale**: User spec explicitly requests LLM-generated comments; existing bot uses templates for confirmations but Gemini for natural language elsewhere. Structured prompt keeps required facts (category, pace, daily ¥) while allowing tone variation.

**Alternatives considered**:
- Templates only — rejected; conflicts with spec input and FR-008 wording.
- LLM-only without computed facts — rejected; risks wrong daily budget numbers.

---

## Decision 5: Integration hook points

**Decision**:
1. **New expense**: After `insert_expenses` in `message_handler._enrich_and_persist_items` (and image path), call `maybe_prepend_budget_pace_warning(reply_text, items, tenant, language)` before returning `BotReply`.
2. **Reply-edit**: After successful `update` in `reply_edit.apply_edit_intent` when `amount` or `category_code` changed, prepend to `format_edit_result` summary via same helper.

**Rationale**: Persistence must complete first so `get_budget_summary` includes the new/changed expense. Central helper avoids duplicating prepend logic across text/image/reply paths.

**Alternatives considered**:
- Supabase trigger pushing LINE messages — out of scope; not tied to confirmation reply.
- Middleware in `format_expense_items` — rejected; runs before persist in some paths.

---

## Decision 6: Fiscal month from RPC, not hardcoded calendar

**Decision**: Pass `budget_month` derived from expense `expense_date` into `get_budget_summary`. Use RPC-returned `days_in_month`, `elapsed_days`, and `fiscal_start_day` metadata.

**Rationale**: Production DB supports custom fiscal start via `tenant_settings` (post-012). Hardcoding calendar JST would desync bot warnings from web dashboard for tenants with non-default fiscal start.

**Alternatives considered**:
- Always current calendar month in JST — rejected after reviewing `20260626120000_tenant_settings.sql`.

---

## Decision 7: Category display names from `category_nodes`

**Decision**: Fetch `name_ja` (and `code` fallback) for warned bucket `category_node_id` via a lightweight Supabase select or reuse data already on enriched expense rows / confirmation snapshot.

**Rationale**: Warnings must name the category (FR-007). L1/L2 names are tenant-scoped in `category_nodes`.

**Alternatives considered**:
- Category code only (e.g. `food.dining`) — rejected; poor UX in Japanese replies.
