# Research: Bot Reply Language Override

## Decision 1: Storage location

**Decision**: Store override on `tenant_settings.reply_language` (nullable).

**Rationale**: Bot behavior settings are already tenant-scoped (persona, confirmation item details). Placing reply language there keeps one settings surface and one persistence path for the web UI.

**Alternatives considered**:
- Write into `user_language_preferences` with a new `web_settings` source — mismatches tenant-scoped bot behavior UI and group semantics.
- New table — unnecessary for a single nullable enum field.

## Decision 2: Precedence

**Decision**: Tenant override (when non-null) wins over personal language preferences and chat language requests for replies in that tenant. When null, keep existing `resolve_reply_language` behavior.

**Rationale**: Matches the product ask (“web app user can override”). Chat phrases still update personal prefs for Default mode and other tenants.

## Decision 3: Language codes

**Decision**: Persist `en`, `ja`, `zh` only; UI labels English / Japanese / Chinese; Default = `null`.

**Rationale**: Matches existing bot i18n (`normalize_reply_language` / confirmation strings).
