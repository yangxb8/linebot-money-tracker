# Tasks: Bot Reply Language Override

## Phase 1 — Data

- [x] T001 Add Supabase migration for `tenant_settings.reply_language`
- [x] T002 Apply migration to remote Supabase project

## Phase 2 — Bot

- [x] T003 Extend `TenantBotSettings` / fetch to return `reply_language` override
- [x] T004 Apply tenant override in webhook language resolution (`main.py`)
- [x] T005 Add pytest coverage for override precedence and fail-open

## Phase 3 — Web

- [x] T006 Extend settings types + server/client/API for `reply_language`
- [x] T007 Add reply-language control to `BotBehaviorSetting` + i18n strings

## Phase 4 — Verify

- [x] T008 Run pytest and web lint/tests
- [x] T009 Update agent context / feature.json already pointing at 019
