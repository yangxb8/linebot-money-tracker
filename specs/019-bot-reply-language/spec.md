# Feature Specification: Bot Reply Language Override

**Feature Branch**: `cursor/bot-reply-language-ac14`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Add a new feature in web app setting > bot behavior. To change the reply language, current line bot will reply in user system language setting, make it default. But in web app user can override to use EN, JP or chinese"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Default keeps system language (Priority: P1)

A household member uses the LINE bot without changing reply language in the web app. The bot continues to reply in the language derived from the user’s system/LINE profile language (existing behavior).

**Why this priority**: Must not regress today’s experience for users who never open settings.

**Independent Test**: With reply language set to Default (or unset), send an expense message; confirm the reply language still follows the user’s system/LINE profile preference.

**Acceptance Scenarios**:

1. **Given** no reply-language override is configured for the tenant, **When** a user messages the bot, **Then** replies use the existing system/LINE-profile language resolution.
2. **Given** the settings page shows reply language as Default, **When** the user saves other bot-behavior settings, **Then** reply language remains Default (no accidental override).

---

### User Story 2 - User overrides reply language from web settings (Priority: P1)

A user opens Settings → LINE bot behavior and chooses English, Japanese, or Chinese as the reply language. After saving, subsequent bot replies for that tenant use the selected language.

**Why this priority**: This is the core value of the feature.

**Independent Test**: Set reply language to English in web settings, then message the bot; verify the next reply is in English regardless of LINE profile language. Repeat for Japanese and Chinese.

**Acceptance Scenarios**:

1. **Given** a user opens bot behavior settings, **When** they select English and save, **Then** the next bot reply for that tenant is in English.
2. **Given** a user selects Japanese and saves, **When** they later reopen the settings page, **Then** Japanese is shown as the current selection.
3. **Given** a user selects Chinese and saves, **When** they log an expense or trigger an error reply, **Then** those replies are in Chinese.

---

### User Story 3 - Reset to Default restores system language (Priority: P2)

A user who previously forced a language returns the setting to Default. Bot replies again follow system/LINE profile language.

**Why this priority**: Users need a clear way to undo the override without support intervention.

**Independent Test**: Set English override, confirm English replies, switch back to Default, confirm replies again follow system language.

**Acceptance Scenarios**:

1. **Given** a tenant has an English override, **When** the user sets reply language back to Default and saves, **Then** subsequent replies follow system/LINE profile language again.
2. **Given** reply language is Default, **When** the user’s LINE profile language is Chinese, **Then** bot replies are in Chinese.

---

### Edge Cases

- Invalid saved values (unknown language codes) must be treated as Default and must not break replies.
- Temporary failure loading tenant settings must fall open to existing system-language resolution.
- Group/shared tenants: the override applies to bot replies in that tenant scope for all members.
- Concurrent settings edits: last successful save wins.
- Chat phrases like “英語で” continue to update personal language preferences, but an active tenant web override takes precedence for replies in that tenant.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST keep system/LINE-profile language resolution as the default reply-language behavior when no override is set.
- **FR-002**: The web Settings → LINE bot behavior page MUST expose a reply-language control with options: Default (system language), English, Japanese, and Chinese.
- **FR-003**: Users MUST be able to view the currently saved reply-language selection for the selected tenant.
- **FR-004**: Users MUST be able to save a reply-language override of English, Japanese, or Chinese for the selected tenant.
- **FR-005**: Users MUST be able to clear the override by selecting Default and saving.
- **FR-006**: When a tenant override is set, the LINE bot MUST use that language for subsequent replies in that tenant context.
- **FR-007**: When no override is set (or settings cannot be loaded), the bot MUST continue using existing system/LINE-profile language resolution.
- **FR-008**: The system MUST reject or normalize invalid language values so only supported languages (or Default) are persisted.
- **FR-009**: Reply-language changes MUST take effect for subsequent bot replies without reinstalling or re-linking LINE.

### Key Entities *(include if feature involves data)*

- **Reply language override**: Optional tenant-scoped preference forcing bot reply language to English, Japanese, or Chinese; unset means Default (system language).
- **Bot behavior settings**: Existing settings collection that already includes persona and confirmation display options; extended with reply language.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With Default selected, 100% of tested replies still follow system/LINE-profile language (no regression).
- **SC-002**: After saving English, Japanese, or Chinese, 100% of tested subsequent replies for that tenant use the selected language across at least two reply types (confirmation and error/help).
- **SC-003**: Returning to Default restores system-language behavior in the next reply in 100% of tested cases.
- **SC-004**: Users can find and change reply language from Settings → bot behavior in under 1 minute without external help.
- **SC-005**: Invalid or missing override values never prevent the bot from replying.

## Assumptions

- Supported languages match existing bot i18n: English (`en`), Japanese (`ja`), Chinese (`zh`).
- Override is tenant-scoped (same as other bot behavior settings), not a separate per-web-user preference table.
- “System language” means the existing LINE profile / personal language preference resolution already used by the bot.
- When a tenant override is active, it takes precedence over personal language preferences and chat language requests for replies in that tenant.
- Web dashboard auth and tenant access checks remain unchanged.
