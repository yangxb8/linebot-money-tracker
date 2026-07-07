# Contract: Bot Persona Resolution & Application

**Feature**: `016-bot-persona-settings`  
**Created**: 2026-07-07

## Overview

The bot must apply an “active persona” to all replies, based on tenant-scoped settings. This contract defines how the bot resolves persona settings and how failures are handled.

## Inputs

- `tenant_type`: `user` | `group` | `room`
- `tenant_id`: string
- `reply_language`: string (existing language resolution remains source of truth)
- `raw_reply_text`: the bot’s reply content before persona styling

## Outputs

- `styled_reply_text`: the final reply text to send

## Resolution rules

1. Load tenant settings for (`tenant_type`, `tenant_id`).
2. Normalize persona fields:
   - If preset missing/invalid → default preset (`judy_hopps_cute_firm`)
   - If emoji level missing/invalid → default emoji level (normal)
   - If custom text too long/invalid → drop custom text (but still apply preset)
3. Apply persona styling in a single centralized formatting step so it affects all reply types.

## Application rules

- Persona styling may modify:
  - greeting/closing
  - punctuation/emoji usage
  - short “voice” phrases that do not alter factual content
- Persona styling must not:
  - change amounts, dates, IDs, or category names
  - remove or re-order critical structured content users rely on
  - reduce clarity of error messages

## Failure handling (fail-open)

- If settings lookup fails or throws:
  - Use default persona
  - Return a reply (never block the reply path)

## Observability

- Log only minimal signals (e.g., “persona_lookup_failed”) without logging persona custom text.
