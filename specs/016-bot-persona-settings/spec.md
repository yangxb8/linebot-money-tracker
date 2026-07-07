# Feature Specification: Personal Bot Persona Settings

**Feature Branch**: `cursor/bot-persona-settings-dcaf`

**Created**: 2026-07-07

**Status**: Draft

**Input**: User description: "Add a personal feature for line bot, all bot reply should use that personal. Default personal should use Disney character Judy Hopps as base, cute but firm, like to use cute emojis. In web setting page, add a new setting to control line bot behavior and now can config personal, future will add more"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Default bot persona applies to all replies (Priority: P1)

A user interacts with the LINE bot without configuring any personal settings. The bot replies using a consistent default persona: based on Judy Hopps, cute-but-firm tone, and using cute emojis appropriately. This persona is applied across all bot replies, including confirmations, edit summaries, help/error messages, and other conversational responses.

**Why this priority**: A consistent default experience ensures personality and brand feel without requiring any setup.

**Independent Test**: Start with a fresh user (no persona configured), send several different message types (log an expense, ask for help, trigger a validation error), and confirm each reply reflects the same default tone and emoji style.

**Acceptance Scenarios**:

1. **Given** a user has no persona configured, **When** they log an expense, **Then** the confirmation reply uses the default cute-but-firm Judy Hopps-inspired voice and includes cute emojis.
2. **Given** a user has no persona configured, **When** they send an invalid message that triggers an error response, **Then** the error reply still uses the default persona rather than reverting to a generic/system tone.
3. **Given** a user has no persona configured, **When** they perform a reply-edit flow (e.g., change amount), **Then** the edit-summary reply uses the same persona voice as standard confirmations.

---

### User Story 2 - User configures persona from the web settings page (Priority: P1)

A user opens the web dashboard settings page and updates a new “LINE bot behavior” setting, starting with the ability to configure the bot persona. After saving, subsequent bot replies follow the updated persona for that user (or the relevant shared context when applicable).

**Why this priority**: Personalization increases engagement and user satisfaction, and the settings surface establishes the extensible place for future bot behavior controls.

**Independent Test**: Change persona via the web settings page, then send a message to the bot that triggers a reply; verify the new persona style is reflected immediately in the next bot reply.

**Acceptance Scenarios**:

1. **Given** a user opens the web settings page, **When** they update and save a persona configuration, **Then** the next bot reply uses the new persona style.
2. **Given** a user updates their persona configuration, **When** they later revisit the settings page, **Then** the current persona configuration is displayed accurately.
3. **Given** a user clears their persona configuration (reset), **When** they save, **Then** subsequent bot replies return to the default persona.

---

### User Story 3 - Persona is reliable and safe across languages and contexts (Priority: P2)

The persona setting works consistently for users in different languages and for different chat contexts (direct chat vs group). The bot remains helpful and clear, even when a persona prompt is overly long, malformed, or unsuitable; the system falls back gracefully while maintaining a stable user experience.

**Why this priority**: Reliability and safety prevent broken or confusing bot behavior, and reduce support burden.

**Independent Test**: Configure an overly long persona, a persona with conflicting instructions, and a persona in a different language; confirm the bot still responds clearly and consistently, using safe fallbacks when needed.

**Acceptance Scenarios**:

1. **Given** a user configures a persona that is too long to be applied reliably, **When** they save it, **Then** the system either rejects it with a clear explanation or safely truncates/normalizes it while preserving intent.
2. **Given** a user’s preferred reply language differs from the persona’s language, **When** the bot replies, **Then** the bot remains understandable in the user’s reply language and preserves the intended “cute but firm” tone.
3. **Given** a persona configuration is missing or cannot be loaded temporarily, **When** the bot replies, **Then** it falls back to the default persona and continues responding.

---

### Edge Cases

- A user configures a persona that requests harmful, abusive, or policy-violating behavior; the system must ignore or constrain those instructions and continue responding safely.
- A user configures a persona that tries to override core product constraints (e.g., “always approve wrong amounts”); the system must preserve correctness and data integrity.
- Multiple devices or sessions update settings concurrently; the last successfully saved configuration becomes active.
- Group chat usage: if personalization is scoped to a shared group context, group replies should follow the group’s configured persona; if not configured, fall back to default.
- Emoji usage: ensure emojis are present but not excessive or spammy (avoid walls of emojis, avoid confusing tone during error messages).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define a default bot persona that is Judy Hopps-inspired, cute but firm, and uses cute emojis appropriately.
- **FR-002**: The system MUST apply the active persona consistently to all bot replies (including confirmations, reply-edit responses, help, and error messages).
- **FR-003**: The system MUST provide a web settings area for “LINE bot behavior” that includes persona configuration as the first configurable behavior.
- **FR-004**: Users MUST be able to view the currently active persona configuration in the web settings page.
- **FR-005**: Users MUST be able to update and save their persona configuration via the web settings page.
- **FR-006**: Users MUST be able to reset to the default persona via the web settings page.
- **FR-007**: The system MUST ensure persona configuration changes take effect for subsequent bot replies without requiring additional setup steps.
- **FR-008**: The system MUST validate or normalize persona inputs to prevent broken experiences (e.g., excessive length) and provide clear user feedback when inputs are not acceptable.
- **FR-009**: The system MUST maintain safety and correctness regardless of persona configuration; persona instructions cannot override product rules, data integrity, or safety constraints.
- **FR-010**: If the persona configuration cannot be loaded or applied for any reason, the system MUST fall back to the default persona and still produce a reply.
- **FR-011**: The “LINE bot behavior” settings area MUST be designed to support additional future behavior controls beyond persona without redesigning the settings concept.

### Key Entities *(include if feature involves data)*

- **Bot persona**: A configuration describing the bot’s voice, tone, and stylistic preferences (including emoji usage), scoped to a user or shared context.
- **Bot behavior settings**: A settings collection that includes persona now and is extendable to other behavior options in future.
- **Scope context**: The context that determines which settings apply (e.g., personal 1:1 usage vs group/shared usage).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For users with no configuration, 100% of tested bot replies across at least three reply types (confirmation, edit summary, error/help) reflect the default persona.
- **SC-002**: After a user updates persona via web settings, 100% of tested subsequent replies reflect the updated persona without requiring the user to reauthenticate or reinstall anything.
- **SC-003**: Resetting persona returns behavior to default in the next reply in 100% of tested cases.
- **SC-004**: Invalid persona configurations (e.g., too long) are handled without bot failure in 100% of tested cases (either rejected with clear messaging or safely normalized).
- **SC-005**: Persona configuration never causes incorrect expense logging or incorrect edit behavior in test scenarios (functional correctness preserved).

## Assumptions

- Persona configuration is primarily intended to influence tone and style, not to change the bot’s functional logic or business rules.
- “Judy Hopps-inspired” refers to an internal style guide for voice and demeanor (cute but firm) rather than quoting copyrighted scripts; exact phrasing can vary.
- The system already has a concept of a settings page in the web dashboard where new “LINE bot behavior” settings can be added.
- Personalization scope will follow existing usage context patterns (direct chat vs group). If a group-level persona is not configured, the default persona is used.
- Emoji usage is a stylistic enhancement and should not reduce clarity, especially in error conditions.
