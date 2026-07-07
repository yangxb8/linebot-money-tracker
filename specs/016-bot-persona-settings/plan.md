# Implementation Plan: Personal Bot Persona Settings

**Branch**: `cursor/bot-persona-settings-dcaf` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/016-bot-persona-settings/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add tenant-scoped “LINE bot behavior” settings (starting with bot persona) that the bot applies consistently to all replies. Default persona is Judy Hopps-inspired (cute but firm, cute emojis); web settings allow viewing/updating/resetting persona and provide an extendable home for future bot behavior controls.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3 (bot) and TypeScript (web)

**Primary Dependencies**: LINE Bot SDK + Gemini client (bot), Next.js (web), Supabase (shared backend)

**Storage**: Supabase Postgres (tenant-scoped settings stored in `tenant_settings`)

**Testing**: Python pytest for bot, web tests/lint already exist in `web/` (vitest / Next lint)

**Target Platform**: Linux server runtime for bot + Next.js web app

**Project Type**: Chat bot + web dashboard with a shared database

**Performance Goals**: No measurable latency regression in normal reply flows; persona lookup must be low overhead and safe to fail-open.

**Constraints**: Persona must not affect correctness/safety; must degrade gracefully (default persona on failure); inputs must be validated/normalized.

**Scale/Scope**: Tenant-scoped settings for personal (user) and shared (group/room) contexts; future bot behavior controls live alongside persona settings.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate A (Code Quality & Maintainability)**: Persona application should be centralized (single wrapper) to avoid inconsistent tone across reply paths.
- **Gate B (Test-First Delivery)**: Add/update automated tests that prove persona is applied for representative reply paths (confirmation, edit, error/help).
- **Gate C (User Experience Consistency)**: Default persona and configured persona must produce predictable, readable replies (emoji not excessive; errors still clear).
- **Gate D (Performance & Reliability)**: Persona lookup failures must not break replies; always fall back to default persona.
- **Gate E (Observability & Feedback)**: Log safe, minimal signals for persona resolution failures (no secrets; no storing persona text in logs).

## Project Structure

### Documentation (this feature)

```text
specs/016-bot-persona-settings/
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
services/                      # Bot pipeline + reply formatting
web/src/                       # Next.js dashboard + settings UI + settings API route
supabase/migrations/           # Postgres schema + RLS for tenant settings
tests/                         # Bot automated tests (pytest)
```

**Structure Decision**: Extend existing shared `tenant_settings` storage and web settings route/UI to include persona, and add a single bot-side reply styling wrapper applied at the final reply assembly stage.

## Phase 0: Research (output: `research.md`)

Research goals and decisions:
- Decide persona representation (preset id + optional custom instructions vs freeform only).
- Decide scoping (per tenant: user/group/room) and precedence rules.
- Decide where persona is applied in bot reply pipeline (single wrapper location covering all reply types).
- Decide web settings UX for persona (defaults, validation, reset).
- Decide database schema changes (extend `tenant_settings` vs new table) and RLS impact.

## Phase 1: Design (outputs: `data-model.md`, `contracts/`, `quickstart.md`)

Design outputs:
- Data model for tenant settings extensions and persona fields.
- Contracts for the settings API payload and bot persona resolution behavior.
- Quickstart steps for running tests and validating persona changes locally (as much as the environment allows).

## Phase 2: Tasks (output: `tasks.md`, produced by `/speckit-tasks`)

Implementation tasks will be generated after the plan artifacts are complete.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
