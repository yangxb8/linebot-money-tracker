# Research: Personal Bot Persona Settings

**Feature**: [spec.md](./spec.md)  
**Plan**: [plan.md](./plan.md)  
**Created**: 2026-07-07

## Decision 1: Persona scope and precedence

- **Decision**: Store persona settings per tenant (`tenant_type`, `tenant_id`) using the existing `tenant_settings` row, so personal chats use the user tenant and group/room chats use the shared tenant.
- **Rationale**: The project already models “scope context” as a tenant (`user`, `group`, `room`) and already uses `tenant_settings` for tenant-scoped configuration (fiscal start day).
- **Alternatives considered**:
  - Store only per-user settings and apply in all contexts (rejected: group chats need a shared personality option).
  - Store per-user + per-group overrides with precedence (rejected for v1: extra complexity; can be added later if needed).

## Decision 2: Representation of “persona”

- **Decision**: Use a safe, structured persona configuration:
  - `persona_preset`: a small set of curated presets (v1: `judy_hopps_cute_firm` plus `default` alias)
  - `persona_custom_text`: optional short “style notes” text that can refine tone but cannot override safety/correctness rules
  - `emoji_level`: bounded enum-like value (e.g., `off`, `light`, `normal`) to control emoji intensity
- **Rationale**: Presets keep replies consistent and safe while still allowing personalization; bounded fields are easier to validate and test than unconstrained freeform prompts.
- **Alternatives considered**:
  - Freeform persona prompt string only (rejected: harder to validate; higher risk of unsafe/erratic behavior; difficult to ensure “all replies” consistency).
  - Hardcode only one persona, no settings (rejected: contradicts requirement to configure persona and future settings).

## Decision 3: Where persona is applied in the bot pipeline

- **Decision**: Apply persona in one centralized “final reply formatting” layer that wraps the final `text` returned by the bot pipeline, so confirmations, reply-edits, and error/help replies are all consistently styled.
- **Rationale**: A single choke point prevents drift where some reply paths forget persona handling. The existing pipeline already has a finalization step (`_finalize_expense_reply`) that prepends budget pace warnings; persona styling can be adjacent to that layer conceptually.
- **Alternatives considered**:
  - Apply persona inside each message formatter (rejected: high risk of missing paths; increases duplication).
  - Rewrite all replies via LLM “tone rewrite” (rejected: latency/cost; creates correctness risk for error messages; harder to test deterministically).

## Decision 4: Web settings UX and validation behavior

- **Decision**: Extend the existing Settings area with a new “LINE bot behavior” section that:
  - Shows current persona preset + emoji level + optional custom text
  - Allows updating these values and saving
  - Includes a “Reset to default” action
  - Validates inputs (max lengths; allowed values) and shows clear errors without saving invalid state
- **Rationale**: The project already has a settings page and a server-side settings API; adding a new section is aligned with current UX patterns and sets up a home for future bot behavior toggles.
- **Alternatives considered**:
  - Separate “persona page” without grouping under bot behavior (rejected: future settings would fragment).

## Decision 5: Storage and migration strategy

- **Decision**: Extend `tenant_settings` with additional persona-related columns rather than creating a new table for v1.
- **Rationale**: Keeps settings reads/writes simple and tenant-scoped; reduces joins and RLS policy complexity.
- **Alternatives considered**:
  - New table `tenant_bot_settings` (rejected for v1: additional RLS and API complexity with limited benefit).

## Open follow-ups (explicitly deferred)

- Add additional persona presets beyond Judy Hopps-inspired default.
- Add per-user override precedence on top of group persona when desired.
- Add additional bot behavior controls in the same settings section (e.g., verbosity level, confirmation format).
