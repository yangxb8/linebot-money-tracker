# Research: Monthly Expense Report

**Feature**: 022-monthly-expense-report  
**Date**: 2026-11-27

## Decision 1: Extend intent with `monthly_report` + phrase gate

**Decision**: Add `monthly_report` to `TextMessageIntent` and the combined classifier prompt. Prefer `monthly_report` over `expense` / `wish_list` / `webapp` when the user clearly asks for a period summary/report (e.g. “monthly report”, “レポート”, “先月のまとめ”, “家計レポート”). Add a deterministic phrase gate (like wish/webapp) for high-precision JP/EN cues before or around LLM classification.

**Rationale**: Spec FR-001/FR-002 require a dedicated request category distinct from expense and wish flows. Existing four-way intent already gates `message_handler` before persist.

**Alternatives considered**:
- Phrase-only without LLM — rejected; multilingual paraphrases need classifier backup.
- Post-expense “summary” command only — rejected; conflicts with natural-language ask requirement.

---

## Decision 2: Fiscal periods via existing `fiscal_start_day` (会計月の開始日)

**Decision**: Reuse `services/budget_pace.py` helpers (`_fetch_fiscal_start_day`, `fiscal_period_start_for_date`) for period boundaries. Default report target = **previous completed** fiscal period relative to “today” in JST. Named periods (“先月”, “this month”, “October”) map onto fiscal periods, not raw calendar labels when start day ≠ 1.

**Rationale**: Clarifications require consuming 設定 → 会計月の開始日 and aligning budget comparison with the same windows used by pace/budget features.

**Alternatives considered**:
- Always calendar month — rejected; contradicts product setting and clarifications.
- New cycle editor in this feature — rejected; setting already exists on web 設定.

---

## Decision 3: Persist artifacts + tips in Postgres; PNG in Supabase Storage

**Decision**:
- Table `monthly_report_artifacts`: one logical report per `(tenant, period_start)` with status, fingerprint, storage path, insight text, style metadata.
- Table `monthly_report_tips`: unique `(tenant, conversation_scope, tip_period_start)` to enforce once-per-conversation tip (for groups, conversation = group/room tenant).
- Storage bucket `monthly-reports` (private); service role uploads PNG; generate **signed HTTPS URLs** for LINE `ImageMessage` (`originalContentUrl` / `previewImageUrl`).

**Rationale**: LINE cannot accept raw bytes in reply; URLs must be HTTPS. Ask-again delivery happens after the reply token is consumed, so artifacts must outlive the first turn. Fingerprint enables FR-011 refresh when expenses/budgets change.

**Alternatives considered**:
- Ephemeral in-memory only — rejected; multi-instance Cloud Run and ask-again require durable state.
- Store PNG as bytea in Postgres — rejected; large rows and awkward LINE URL serving.
- Public CDN without auth — rejected; prefer signed URLs with short TTL.

---

## Decision 4: Same-turn budget (~8s) then ask-again; background finish

**Decision**: On first ask (or refresh), start prepare and wait up to ~**8 seconds**. If ready, deliver image in the same reply. If not, reply with preparing/ask-again text, continue prepare via `asyncio.create_task` (or equivalent non-blocking continuation), and mark `ready`/`failed` when done. Later asks: deliver if ready; in-progress text if still preparing; restart on failure.

**Rationale**: Matches clarification Option B (same-turn when soon; else ask again) and SC-001/SC-002 without unsolicited image push. LINE reply tokens are single-use; background completion must not attempt to reuse the old token.

**Alternatives considered**:
- Always two-step — rejected by clarification.
- Always block until done — rejected; risks webhook timeouts and silent drops.
- External queue (Cloud Tasks) in v1 — deferred; in-process task sufficient for household scale if failures are retried on next ask.

---

## Decision 5: Primary chart = total + ≤3 worst-variance categories (Pillow)

**Decision**: When a total budget exists, always plot total budget vs actual. When category budgets exist, add up to **3** worst-variance categories ranked by overspend amount, then by pace ratio (ahead-of-pace), deterministic tie-break by category id. Render with **Pillow** (already a dependency) into one PNG: fixed layout frame, chart, commentary block. LLM (metered Gemini) drafts commentary from snapshot facts with template fallback (persona/i18n). No matplotlib dependency.

**Rationale**: Clarification Option C; phone readability; Pillow already used for fixtures; avoids new heavy charting stack.

**Alternatives considered**:
- Every budgeted L1/L2 on chart — rejected; unreadable on mobile.
- Category share as primary when budgets exist — rejected; app focus is meeting budget.
- External chart SaaS — rejected; unnecessary latency/secrets.

---

## Decision 6: Extend `BotReply` for optional image; harness writes file

**Decision**: Extend `BotReply` with optional image fields (e.g. `image_url` + `preview_url`, or `image_bytes` for harness). `main.py` sends `TextMessage` caption and/or `ImageMessage` when URLs present. `local_run.py` writes PNG under a local path / artifacts and prints it when bytes are available (signed URL optional offline).

**Rationale**: Spec allows a short caption with the single image; current `BotReply` is text-only and must evolve for LINE image send.

**Alternatives considered**:
- Separate reply channel only in `main.py` — rejected; harder to test via handler return value.
- Flex Message instead of image — rejected; spec requires one image with graph + comments.

---

## Decision 7: New-period tip is text-only and does not start prepare

**Decision**: On first inbound message for a ledger conversation in a new fiscal period, prepend/append a short i18n tip that the previous period’s report is available when they ask. Record tip in `monthly_report_tips`. Do **not** start image generation from the tip alone. Group: once per conversation/period. If the first message is itself `monthly_report`, report flow takes precedence (tip omitted or folded).

**Rationale**: Clarifications Option B for tip + Option B for group once-per-conversation; FR-016; avoids tip-triggered cost/latency.

**Alternatives considered**:
- Tip starts background prepare — rejected; violates “lazy on report ask” and assumptions.
- Per-member tip in groups — rejected by clarification.

---

## Decision 8: Test expansion in bot functional suite (no web e2e in v1)

**Decision**: Expand `tests/functional/bot/` with mocked journeys for: intent routing, default previous period + fiscal_start_day, same-turn ready vs ask-again, tip once, budget-primary graph snapshot inputs, zero expense/no budget, no expense side effects. Unit-test period math, variance ranking, render smoke (PNG header). Skip new Playwright/web tests because there is no web surface in v1.

**Rationale**: Constitution Test-First Delivery + AGENTS.md suite expansion; bot-only scope.

**Alternatives considered**:
- Manual quickstart only — rejected; incomplete per constitution.
- Web dashboard smoke — out of scope for v1 feature surface.
