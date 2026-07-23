# Implementation Plan: Bot Reply Language Override

**Branch**: `cursor/bot-reply-language-ac14` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/019-bot-reply-language/spec.md`

## Summary

Extend Settings → LINE bot behavior with a tenant-scoped reply-language control. Default (`null`) keeps today’s LINE-profile / personal language resolution. Selecting English, Japanese, or Chinese stores an override on `tenant_settings` and forces bot replies for that tenant to the chosen language.

## Technical Context

**Language/Version**: Python 3.11+ (LINE bot); TypeScript/React (Next.js web); SQL (Supabase Postgres)

**Primary Dependencies**: Existing `user_language.resolve_reply_language`, `tenant_settings` / bot persona settings APIs, web settings route + `BotBehaviorSetting`

**Storage**: Supabase Postgres — add nullable `tenant_settings.reply_language` checked to `en|ja|zh`

**Testing**: pytest for override precedence and fail-open; web settings types/API wiring covered by existing lint/typecheck path

**Target Platform**: LINE bot (Cloud Run) + Next.js web dashboard + Supabase

**Project Type**: Chat bot + web dashboard + shared Supabase backend

**Performance Goals**: One extra nullable column read on existing tenant settings fetch; no additional LLM calls

**Constraints**:
- Default must preserve current system-language behavior
- Override is tenant-scoped (aligned with bot behavior settings)
- Fail open to existing resolution when settings unavailable/invalid
- Active override takes precedence over personal prefs / chat language requests

**Scale/Scope**: Household tenants; single setting per tenant

## Constitution Check

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Extend existing settings + language resolution paths; no parallel preference system |
| Test-First Delivery | pytest for override precedence before wiring production path |
| User Experience Consistency | Control lives in existing bot behavior settings page with i18n labels |
| Performance & Reliability | Fail-open; no new network hops beyond existing tenant settings fetch |
| Observability & Feedback | Reuse existing language logging; invalid values normalized |

**Gate**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/019-bot-reply-language/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── settings-reply-language.md
└── tasks.md
```

### Source Code

```text
supabase/migrations/YYYYMMDDHHMMSS_tenant_settings_reply_language.sql
services/tenant_settings.py
services/user_language.py          # optional helper / keep resolve separate
main.py                            # apply tenant override after base resolve
web/src/lib/settings/{types,server,client}.ts
web/src/app/api/settings/route.ts
web/src/components/settings/BotBehaviorSetting.tsx
web/src/lib/i18n/messages.ts
tests/test_user_language.py / new override tests
```

## Implementation Approach

1. Add `reply_language` nullable column to `tenant_settings`.
2. Extend Python `fetch_tenant_bot_settings` (or thin helper) to return override.
3. In webhook/handler language resolution: base language via existing `resolve_reply_language`; if tenant override present, use override.
4. Extend web settings GET/PUT + Bot Behavior UI select: Default / English / Japanese / Chinese.
5. Add pytest coverage for override precedence and invalid/null handling.
