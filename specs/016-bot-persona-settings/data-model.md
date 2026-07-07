# Data Model: Personal Bot Persona Settings

**Feature**: [spec.md](./spec.md)  
**Created**: 2026-07-07

## Entity: Tenant settings (existing, extended)

**Purpose**: Store tenant-scoped configuration values that affect budgeting and bot behavior.

**Primary key**: (`tenant_type`, `tenant_id`)

**Existing fields**
- `tenant_type` (text): One of `user`, `group`, `room`
- `tenant_id` (text): Identifier for the tenant scope
- `fiscal_start_day` (smallint): 1–28
- `updated_at` (timestamptz)

**New fields (this feature)**
- `bot_persona_preset` (text, nullable): Preset identifier (e.g., `judy_hopps_cute_firm`)
- `bot_persona_custom_text` (text, nullable): Optional short style notes provided by the user
- `bot_persona_emoji_level` (smallint, nullable): Bounded level (e.g., 0=off, 1=light, 2=normal)
- `bot_persona_updated_at` (timestamptz, nullable): Last update timestamp for persona settings (independent of other settings)

**Validation rules**
- `bot_persona_preset` must be one of an allowlist of supported presets
- `bot_persona_custom_text` must be bounded in length and must not be treated as executable instructions
- `bot_persona_emoji_level` must be within an allowlist/range

**Relationships**
- None required (kept denormalized in `tenant_settings` for v1)

## Entity: Bot persona (logical, not necessarily stored)

**Purpose**: The effective persona used to render replies.

**Fields**
- `preset_id`: resolved preset (default to Judy Hopps-inspired preset when unset)
- `style_notes`: normalized custom text (may be empty)
- `emoji_level`: normalized bounded value

**Resolution**
- The bot resolves the active persona by tenant (`tenant_type`, `tenant_id`) and falls back to default when missing/unavailable/invalid.

## State transitions

### Persona configuration lifecycle (per tenant)

1. **Unset** → uses default persona
2. **Set** (preset and/or custom text) → applies configured persona
3. **Reset** → clears persona fields → returns to default

### Failure handling

- If settings lookup fails, schema mismatches, or values are invalid: treat as **Unset** and continue replying with default persona.
