# Monthly Report Artifact Contract

**Feature**: 022-monthly-expense-report  
**Type**: Internal Python service API (not a public HTTP route)

## Module surface

Primary orchestration: `services/monthly_report.py`

| Function | Behavior |
| -------- | -------- |
| `resolve_report_period(tenant, user_text, *, as_of) -> ReportPeriod \| Error` | Default previous completed; parse named current/past; reject future |
| `maybe_new_period_tip(tenant, *, as_of) -> str \| None` | Once per conversation/period; persists tip row |
| `handle_monthly_report_ask(tenant, user_text, gemini, context) -> BotReply` | Full ask path including prepare/deliver |
| `ensure_artifact(tenant, period, *, force_refresh=False) -> ArtifactState` | Load/create; kick prepare |

Supporting modules:

- `monthly_report_period.py` — fiscal window math
- `monthly_report_snapshot.py` — budget vs actual + worst-variance (≤3)
- `monthly_report_insights.py` — commentary (LLM + template fallback)
- `monthly_report_render.py` — Pillow PNG
- `monthly_report_repository.py` — DB + Storage

## Same-turn prepare semantics

```text
start_prepare(artifact_id)
wait up to SAME_TURN_BUDGET_SECONDS (~8)
if ready → BotReply(text=caption, image=urls)
else → BotReply(text=preparing); background continues to ready/failed
```

Background completion MUST NOT call LINE with the expired reply token. Delivery happens on a later user ask (new reply token) or harness print.

## Fingerprint invalidation

On ask, recompute `data_fingerprint` from:

- Expense rows in period (ids, amounts, categories, deleted flags)
- Budget rows for period
- `fiscal_start_day`

If stored fingerprint differs from ready artifact → treat as stale → `preparing` refresh (same same-turn rules).

`style_fingerprint` changes (persona/language/emoji) also force refresh so on-image copy matches settings.

## Snapshot ranking (worst-variance)

For category budgets:

1. Prefer categories with `spent > limit` ordered by `(spent - limit)` desc
2. Else prefer ahead-of-pace (`pace_ratio > 1`) by `pace_ratio` desc
3. Tie-break `category_node_id` asc
4. Take at most **3**

Total bucket always included in graph when total budget exists.

## Image composition requirements

- One PNG, consistent layout family
- Primary visual: budget vs actual bars/columns for total + selected categories
- Commentary block uses insight text (reply language + persona tone + emoji level)
- Overspend severity adjusts caution styling
- Accent/theme from highest-spend category (deterministic)
- Fallback graph when `has_any_budget` is false (spending summary + “no budget set” copy)

## LINE URL rules

- `original_url` / `preview_url` MUST be HTTPS
- Prefer signed URLs with TTL long enough for LINE to fetch (e.g. ≥10 minutes)
- Preview MAY be the same PNG resized/compressed ≤ LINE preview guidance
