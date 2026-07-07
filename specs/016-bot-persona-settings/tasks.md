# Tasks: Personal Bot Persona Settings

**Input**: Design documents from `specs/016-bot-persona-settings/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish scaffolding and shared constants for persona settings across bot + web.

- [x] T001 Define persona preset(s) + validation constants in `services/bot_persona.py`
- [x] T002 [P] Extend web settings types to include persona fields in `web/src/lib/settings/types.ts`
- [x] T003 [P] Add shared i18n strings for new settings UI labels in `web/src/lib/i18n/messages.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Storage + API wiring needed before any user story can be completed end-to-end.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Add migration to extend `tenant_settings` with persona columns in `supabase/migrations/` (new migration file)
- [x] T005 Update settings read/write server logic to include persona fields in `web/src/lib/settings/server.ts`
- [x] T006 Update settings API route to accept/return persona fields in `web/src/app/api/settings/route.ts`
- [x] T007 Add bot-side tenant settings fetch abstraction in `services/tenant_settings.py` (read persona fields; fail-open defaults)
- [x] T008 Add bot-side persona resolution + normalization in `services/bot_persona.py` (preset allowlist, emoji level bounds, custom text length)

**Checkpoint**: Settings storage + API return persona fields; bot can resolve an effective persona for any tenant (with safe defaults).

---

## Phase 3: User Story 1 - Default bot persona applies to all replies (Priority: P1) 🎯 MVP

**Goal**: All bot replies consistently use the default Judy Hopps-inspired persona when no custom persona is configured.

**Independent Test**: Run bot tests for representative reply paths (confirmation, reply-edit summary, error/help). Verify persona wrapper is invoked and output includes default style cues (tone/emoji rules) without altering factual content.

### Implementation for User Story 1

- [x] T009 [US1] Implement centralized persona “final reply styling” function in `services/bot_persona.py` (input raw text + language + persona config → styled text)
- [x] T010 [US1] Apply persona styling in the final reply assembly for expense confirmations in `services/message_handler.py`
- [x] T011 [US1] Apply persona styling for reply-edit responses in `services/message_handler.py` (ensure edit summary path is covered)
- [x] T012 [US1] Apply persona styling for canned/error/help replies in `services/message_handler.py` (unsupported/error/parse/usage-limit/webapp link paths)
- [x] T013 [US1] Add automated tests asserting persona is applied for 3+ reply types in `tests/test_message_handler_reply.py`

**Checkpoint**: With no persona configured, bot replies consistently reflect default persona across reply types, and tests pass.

---

## Phase 4: User Story 2 - User configures persona from the web settings page (Priority: P1)

**Goal**: User can view/update/reset persona via web settings; subsequent bot replies reflect the saved persona for that tenant.

**Independent Test**: Using the web settings API route, update persona fields for a tenant and verify the API returns updated values. In bot tests (or local harness with keys), confirm a subsequent reply uses the configured persona and reset returns to default.

### Implementation for User Story 2

- [x] T014 [P] [US2] Add “LINE bot behavior” entry in settings navigation in `web/src/components/settings/SettingsMenu.tsx`
- [x] T015 [P] [US2] Create a new settings UI component for persona configuration in `web/src/components/settings/BotBehaviorSetting.tsx`
- [x] T016 [US2] Add a new settings route/page for bot behavior in `web/src/app/(app)/settings/bot-behavior/page.tsx`
- [x] T017 [US2] Wire settings client calls for persona fields in `web/src/lib/settings/client.ts`
- [x] T018 [US2] Implement reset-to-default behavior in UI (clears persona fields) in `web/src/components/settings/BotBehaviorSetting.tsx`
- [x] T019 [US2] Add bot-side settings lookup integration (tenant → fetch persona fields) in `services/tenant_settings.py` and use in `services/message_context.py` / `services/message_handler.py` as the source of active persona

**Checkpoint**: Web settings page can read/write persona fields; bot reads tenant persona settings and reflects changes in replies.

---

## Phase 5: User Story 3 - Persona is reliable and safe across languages and contexts (Priority: P2)

**Goal**: Persona inputs are validated/normalized; bot never breaks replies and always falls back to defaults; style does not corrupt factual content; behavior works for user + group tenants.

**Independent Test**: Submit invalid persona values via API, verify server returns 400 with stable error code; simulate missing/invalid settings and verify bot falls back to default persona; confirm group tenant vs user tenant resolution is correct.

### Implementation for User Story 3

- [x] T020 [US3] Add server-side validation for persona fields (preset allowlist, custom text max length, emoji level bounds) in `web/src/lib/settings/server.ts`
- [x] T021 [US3] Add API error mapping + UI error display for invalid persona inputs in `web/src/components/settings/BotBehaviorSetting.tsx`
- [x] T022 [US3] Ensure bot persona styling never changes numbers/IDs by implementing conservative styling rules in `services/bot_persona.py`
- [x] T023 [US3] Add bot tests for fail-open behavior (settings load failure → default persona) in `tests/test_message_handler.py`
- [x] T024 [US3] Add tests for tenant scoping (user vs group/room) persona selection in `tests/test_message_handler.py`

**Checkpoint**: Invalid inputs are rejected clearly; bot never fails to reply due to persona; defaults apply reliably; tenant scoping works.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation alignment, performance checks, and final validation.

- [ ] T025 [P] Update docs to reference new bot behavior setting in `specs/016-bot-persona-settings/quickstart.md` (if implementation details changed)
- [x] T026 Run full bot test suite and ensure no regressions: `python3 -m pytest -q`
- [x] T027 Run web checks: `cd web && npm run lint && npm test && npm run build`
- [ ] T028 Review UX for emoji usage and error clarity; adjust defaults in `services/bot_persona.py` and UI copy in `web/src/lib/i18n/messages.ts`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1; blocks all user stories.
- **User Stories (Phase 3–5)**: Depend on Phase 2.
- **Polish (Phase 6)**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2; independent MVP.
- **US2 (P1)**: Depends on Phase 2 and becomes end-to-end once bot settings lookup is wired.
- **US3 (P2)**: Builds on Phase 2; can be developed largely in parallel with US2 once core schema/API is in place.

### Parallel Opportunities

- **Phase 1**: T001–T003 can be parallelized (different files).
- **US2**: UI tasks T014–T016 can be parallel with client wiring T017.
- **US3**: Validation work T020–T021 can be parallel with bot-side tests T023–T024 once shared interfaces stabilize.

---

## Parallel Example: User Story 2

```bash
Task: "Add settings menu entry in web/src/components/settings/SettingsMenu.tsx"
Task: "Create persona settings component in web/src/components/settings/BotBehaviorSetting.tsx"
Task: "Add settings page route in web/src/app/(app)/settings/bot-behavior/page.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2 (schema/API + bot resolution primitives).
2. Complete US1 (centralized persona wrapper + apply in all reply paths + tests).
3. Stop and validate: ensure persona never changes factual content and does not regress existing reply formatting.

### Incremental Delivery

1. US1: default persona everywhere
2. US2: web-configurable persona
3. US3: validation + reliability + tenant scoping hardening
