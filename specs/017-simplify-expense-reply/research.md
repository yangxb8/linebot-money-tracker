# Research: Simplify LINE expense confirmation replies

**Feature**: [spec.md](./spec.md)  
**Plan**: [plan.md](./plan.md)  
**Created**: 2026-07-08

## Decision 1: Amount emphasis in LINE

**Decision**: Use a text-first approach for v1 (receipt-style plain text) with consistent amount placement and symbols; treat true bold/typographic emphasis as optional and only pursue if a richer message type is adopted later.

**Rationale**:
- The existing bot reply pipeline is plain text oriented; keeping confirmation replies as text minimizes UX and implementation risk.
- A consistent “✅ {merchant} ¥{amount} · {category path}” pattern makes the amount visually prominent without relying on formatting features that may not be supported in plain text.

**Alternatives considered**:
- Rich message formats that support typography (more expressive but higher complexity and a larger surface area for regressions).

## Decision 2: Default confirmation layouts

**Decision**:
- **Single item**: one compact receipt line (plus optional small sections like pacing warning).
- **Multi-item**: show category subtotal rows by default (with total count), and only include per-item detail when the user preference is enabled.

**Rationale**:
- Multi-item receipts are the main driver of “too long” confirmations.
- Subtotals preserve the “what did I just log?” value while keeping the message skimmable.

**Alternatives considered**:
- Always show per-item lines (too long).
- Always hide per-item lines without a preference toggle (reduces transparency for users who want details).

## Decision 3: Modular message composition and separators

**Decision**: Introduce a “reply composer” concept that assembles independently constructed message sections (warning, summary, subtotals/details, footer/help) and joins them with a consistent separator strategy.

**Rationale**:
- Supports incremental changes (add/remove sections) without rewriting core business logic.
- Helps maintain UX consistency across confirmation replies and reply-edit summaries.

**Alternatives considered**:
- Inline string building in multiple call sites (hard to test, easy to regress).

## Decision 4: On-demand help instead of always-on instructions

**Decision**: Remove the always-visible edit instruction paragraph from confirmations. Add a small help behavior that returns concise guidance when the user asks how-to questions about edits.

**Rationale**:
- Reduces clutter in the primary success path.
- Keeps discoverability via explicit user intent (“how do I…?”) rather than always showing instructions.

**Alternatives considered**:
- Keep instructions but shorten them (still adds noise to every message).

## Decision 5: Category input mismatch confirmation flow

**Decision**: When the user replies with a category that does not exactly match a category name, the bot guesses a category and requests explicit confirmation by stating the guessed category path and asking the user to reply `YES` before applying the edit (no numbered alternatives by default).

**Rationale**:
- Keeps the interaction compact and unambiguous.
- Avoids reintroducing long suggestion lists into the simplified UX.

**Alternatives considered**:
- Showing numbered alternatives (fast selection but increases message length).
- Asking the user to retype exactly (frustrating).
- Declining to guess (hurts usability).

## Decision 6: Preference scoping (who controls “show item details”)

**Decision**: Default to a tenant-scoped setting for bot behavior, with a clear path to support user-specific overrides if needed.

**Rationale**:
- Shared tenants (groups) benefit from consistent behavior across members.
- A single setting reduces confusion and makes support/debugging easier.

**Alternatives considered**:
- User-only setting (can create inconsistent experiences in groups).
- Always per-user override (more complexity; defer until needed).
