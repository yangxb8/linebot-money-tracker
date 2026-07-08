# Implementation Plan: Simplify LINE expense confirmation replies

**Branch**: `cursor/simplify-expense-reply-format-6ade` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/017-simplify-expense-reply/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Shorten the LINE bot’s expense confirmation replies to a receipt-style format that is easy to skim, while preserving reply-edit functionality. Default multi-item receipts to category subtotals with an optional web setting for per-item detail. Remove always-on “how to edit” instructions and instead answer how-to questions on demand. Use a modular message-composition layer so warning, confirmation, and footer sections are independently constructed and joined with separators.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3 (bot) and TypeScript (web)

**Primary Dependencies**: LINE Bot SDK + Gemini client (bot), Next.js (web), Supabase (shared backend)

**Storage**: Supabase Postgres (existing expense tables + tenant/user settings)

**Testing**: Python pytest for bot; web lint/tests exist in `web/` (Next lint, vitest)

**Target Platform**: Linux server runtime for bot + Next.js web app

**Project Type**: Chat bot + web dashboard with a shared database

**Performance Goals**: No measurable latency regression in confirmation/reply-edit flows; formatting and grouping logic must be low overhead and fail-open.

**Constraints**: Reply-edit must remain safe (only edits when replying to known confirmation). Message formatting must be deterministic enough for users to understand without instructions. Must degrade gracefully if optional sections (budget pace, category mapping, settings lookup) fail.

**Scale/Scope**: Personal and shared tenants (group/room). Typical receipts range 1–20 items. User preference for “show item details” should be tenant-scoped or user-scoped and applied consistently.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate A (Code Quality & Maintainability)**: Introduce a small, testable “reply composer” abstraction rather than scattering formatting conditionals across the message handler.
- **Gate B (Test-First Delivery)**: Add/update automated tests for formatting variants (single item, multi-item subtotals, optional item-detail toggle, edit confirmation YES flow, help responses).
- **Gate C (User Experience Consistency)**: Reply structure must be predictable (headline + key facts), with optional sections clearly separated; avoid walls of text.
- **Gate D (Performance & Reliability)**: Formatting must not depend on external calls; settings/category lookups must fail-open to a safe default.
- **Gate E (Observability & Feedback)**: Keep logs minimal; record safe signals when falling back to default formatting or when help intent triggers (no secrets).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
services/                      # Bot pipeline + reply formatting (confirmation + reply-edit + help)
web/src/                       # Next.js dashboard (bot behavior settings)
supabase/migrations/           # Schema + RLS for settings changes (if needed)
tests/                         # Bot automated tests (pytest)
```

**Structure Decision**: Implement a bot-side reply composer that assembles independently generated sections (pace warning, compact summary, optional subtotals and item detail, footer/help). Add a web setting under the existing settings UI/API so users can choose whether confirmations include per-item detail. Keep reply-edit safety boundaries unchanged.

## Phase 0: Research (output: `research.md`)

Research goals and decisions:
- Decide how “amount emphasis” is achieved within LINE constraints (plain text vs rich message).
- Decide default confirmation layouts for single-item vs multi-item receipts (receipt line + subtotal rows).
- Decide the on-demand help trigger behavior (what counts as a how-to question; language handling).
- Decide how preference is scoped (tenant vs user) and how it is read in bot pipeline.
- Decide how to keep reply-edit targeting usable when per-item lines are hidden (subtotal-level disambiguation prompts).

## Phase 1: Design (outputs: `data-model.md`, `contracts/`, `quickstart.md`)

Design outputs:
- Data model for “confirmation reply display preference” (scope + default + validation).
- Contracts for: confirmation message composition (sections + separators), help intent response, and category guess confirmation (explicit `YES`).
- Quickstart steps for validating formatting variants via tests and local harness flows.

## Phase 2: Tasks (output: `tasks.md`, produced by `/speckit-tasks`)

Implementation tasks will be generated after the plan artifacts are complete.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
