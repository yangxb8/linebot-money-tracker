# Contract: Tenant Settings API (extended for bot persona)

**Feature**: `016-bot-persona-settings`  
**Created**: 2026-07-07

## Overview

The web dashboard reads and updates tenant-scoped settings via a settings API. This feature extends the payload to include “LINE bot behavior” (persona) fields.

## Read settings

**Request**

- Method: `GET`
- Path: `/api/settings`
- Query params:
  - `tenant_type`: `user` | `group` | `room`
  - `tenant_id`: string

**Response (200)**

```json
{
  "fiscal_start_day": 1,
  "bot_persona_preset": "judy_hopps_cute_firm",
  "bot_persona_custom_text": "cute but firm, short replies",
  "bot_persona_emoji_level": 2
}
```

**Defaulting behavior**

- When no settings row exists, return defaults:
  - `fiscal_start_day`: `1`
  - persona fields: omitted or `null` (client treats as default persona)

## Update settings

**Request**

- Method: `PUT`
- Path: `/api/settings`
- Body:

```json
{
  "tenant_type": "user",
  "tenant_id": "U123",
  "fiscal_start_day": 1,
  "bot_persona_preset": "judy_hopps_cute_firm",
  "bot_persona_custom_text": "",
  "bot_persona_emoji_level": 2
}
```

**Response (200)**

```json
{
  "fiscal_start_day": 1,
  "bot_persona_preset": "judy_hopps_cute_firm",
  "bot_persona_custom_text": "",
  "bot_persona_emoji_level": 2
}
```

**Validation / errors**

- Invalid `tenant_type` / `tenant_id`: `400`
- Invalid `fiscal_start_day`: `400` with a stable error code string
- Invalid persona fields (preset not in allowlist, custom text too long, emoji level out of range): `400` with a stable error code string

## Security expectations

- Requests require an authenticated web session.
- Tenant access is enforced server-side (a user can only read/update tenants they can access).
