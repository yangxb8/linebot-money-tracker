# Implementation Plan: Monthly Expense Report

**Branch**: `cursor/monthly-expense-report-52d2` | **Date**: 2026-11-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/022-monthly-expense-report/spec.md`

## Summary

Add a LINE-bot **monthly expense report**: a dedicated `monthly_report` intent that lazily prepares one summary **image** (primary graph = **budget vs actual** for total + a small worst-variance category set, plus persona-styled commentary). Periods follow **設定 → 会計月の開始日**. Default period is the **previous completed** fiscal period. Same-turn delivery when prepare finishes soon enough; otherwise acknowledge and deliver on a later ask. On the first message of a new fiscal period (once per conversation), send a **text-only** tip that last period’s report is available on ask. Web dashboard delivery is out of scope for v1.

## Technical Context

**Language/Version**: Python 3.11+ (LINE bot at repo root); SQL (Supabase Postgres + Storage)

**Primary Dependencies**: Existing `services/intent.py`, `message_handler.py`, `BotReply`, `budget_pace.py` / `get_budget_summary`, persona/i18n (`confirmation_i18n` / `persona_i18n` / `resolve_persona_for_tenant`), `line-bot-sdk` (`TextMessage` + `ImageMessage`), Pillow (already in `requirements.txt`), Gemini for insight copy (metered), Supabase service-role client

**Storage**: Supabase Postgres — new `monthly_report_artifacts` + `monthly_report_tips` (tenant-scoped); Supabase Storage bucket `monthly-reports` for PNG bytes (signed HTTPS URLs for LINE `ImageMessage`)

**Testing**: `pytest` unit + `tests/functional/bot/` expansion (mocked Gemini/LINE/Supabase) for intent, period resolution, tip once-per-conversation, prepare/ready/ask-again, budget-vs-actual selection, no expense side effects. No web vitest/Playwright required for v1 (bot-only surface).

**Target Platform**: LINE webhook (`main.py`) + `local_run.py` console harness + Supabase

**Project Type**: Chat bot + shared Supabase backend (no new web page in v1)

**Performance Goals**:
- Same-turn attempt budget ≈ **8s** wall time from ask → either image reply or “preparing—ask again”
- After artifact `ready`, follow-up ask delivers image in **&lt;10s** user-perceived wait (SC-002)
- Tip path adds negligible latency (DB read/upsert only)

**Constraints**:
- JPY only; fiscal periods via existing `fiscal_start_day`
- No unsolicited **image** push; tip is text-only
- Group tip once per conversation/period (not per member)
- Must not create expenses or wish-list items
- All user-facing copy through i18n/persona stack
- LINE image send requires public HTTPS URL → Storage signed URL (reply token cannot be reused later)
- Test-suite expansion mandatory (constitution + AGENTS.md)

**Scale/Scope**: Household tenants; one artifact per ledger/period/style fingerprint; typically one prepare per period until data changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | New `services/monthly_report*.py` modules; reuse budget_pace, intent, persona/i18n; no parallel budget math |
| Test-First Delivery | pytest + functional bot scenarios for primary acceptance paths before/with wiring; expand `tests/functional/bot/` |
| User Experience Consistency | Dedicated intent; predictable preparing/ready/fail copy; persona + reply language on tip and on-image text |
| Performance & Reliability | Same-turn budget with ask-again fallback; failed prepare never sends broken image; refresh when data fingerprint changes |
| Observability & Feedback | Log prepare start/ready/fail, tip shown, delivery; clear user messages on empty/future/fail |

**Gate**: PASS (pre- and post-design)

**Post-design re-check**: PASS — bot-only surface; schema + Storage additive; budget reads reuse 012/015 contracts; LINE image delivery via signed URLs documented in contracts.

## Architecture

```text
LINE text
   │
   ▼
message_handler
   ├─ maybe_period_tip (first msg of new fiscal period; once/conversation)
   └─ intent == monthly_report?
         │
         ▼
   monthly_report.request_report(tenant, text, …)
         │
         ├─ resolve period (default: previous completed; honor fiscal_start_day)
         ├─ load/create artifact row (ledger + period_start)
         ├─ if ready & fingerprint match → deliver image (+ caption)
         ├─ if preparing → in-progress text
         └─ else start prepare:
               ├─ within ~8s → deliver image same turn
               └─ else reply “ask again” + finish prepare in background task
```

### Prepare pipeline

```text
expenses + budgets for period
  → Budget Comparison Snapshot (total + worst-variance categories)
  → Gemini insight copy (persona / language / emoji)
  → Pillow compose PNG (layout frame + chart + commentary + overspend/theme accents)
  → upload Storage + mark artifact ready (or failed)
```

## Project Structure

### Documentation (this feature)

```text
specs/022-monthly-expense-report/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── monthly-report-bot.md
│   ├── monthly-report-artifact.md
│   └── supabase-schema-delta.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
supabase/migrations/YYYYMMDDHHMMSS_monthly_report_artifacts.sql
  # tables + storage bucket policies (service role)

services/
├── intent.py                    # add monthly_report intent + prompt/gate
├── message_handler.py           # tip wrapper + monthly_report branch
├── message_context.py           # BotReply optional image payload
├── confirmation_i18n.py         # tip / preparing / ready / fail strings
├── persona_i18n.py              # persona variants for new keys
├── monthly_report.py            # orchestration: request, tip, fingerprint
├── monthly_report_period.py     # fiscal period resolve (reuse budget_pace)
├── monthly_report_snapshot.py   # budget vs actual + worst-variance pick
├── monthly_report_insights.py   # Gemini + template fallback commentary
├── monthly_report_render.py     # Pillow image compose
├── monthly_report_repository.py # artifacts + tips + storage upload/URL
├── monthly_report_i18n.py       # optional dedicated templates
main.py                          # reply TextMessage and/or ImageMessage
local_run.py                     # save/print report image path for harness

tests/
├── test_monthly_report_period.py
├── test_monthly_report_snapshot.py
├── test_monthly_report_render.py
├── test_monthly_report_request.py
└── functional/bot/
    └── test_monthly_report_journey.py
```

**Structure Decision**: Extend existing monorepo (Python bot root + Supabase). No web package changes in v1.

## Implementation Approach

1. **Schema + Storage**: `monthly_report_artifacts`, `monthly_report_tips`, private bucket `monthly-reports` with service-role access; signed URL helper for LINE.
2. **Period + snapshot**: Resolve previous/current/named periods via `fiscal_start_day`; build budget-vs-actual snapshot (total + ≤3 worst-variance categories); fingerprint for invalidation.
3. **Render + insights**: Template-safe commentary (LLM optional with fallback); Pillow PNG with consistent layout, persona language, overspend cues, top-spend theme accent.
4. **Orchestration + BotReply**: Lazy prepare, same-turn vs ask-again, resend/refresh; extend `BotReply` + `main.py` / `local_run.py` for image replies.
5. **Intent + tip**: `monthly_report` intent + phrase gate; once-per-conversation new-period tip (text only) that does not start image prepare.
6. **Tests + quickstart**: Unit + functional bot coverage for FR/SC primary paths; document harness commands.

## Complexity Tracking

> No constitution violations requiring justification.
