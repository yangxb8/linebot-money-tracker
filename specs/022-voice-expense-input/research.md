# Research: Voice Expense Input

**Feature**: 022-voice-expense-input  
**Date**: 2026-11-16

## Decision 1: Transcribe audio → reuse text pipeline

**Decision**: After abuse-limit checks, convert voice to a **plain-text transcript** via Gemini multimodal audio, then invoke the existing **`process_text_message`** path (intent → expense parse / wish-list / unsupported). Do **not** invent a parallel expense JSON-from-audio persist path.

**Rationale**: Spec requires confirmation parity, wish-list intent parity, reply-edit, persona/i18n, and tenant rules identical to text. Reusing the text handler guarantees those behaviors and keeps idempotency / confirmation anchors unchanged.

**Alternatives considered**:
- Single multimodal call that returns expense JSON directly — rejected; bypasses wish-list intent, phrase gates, and assist_parse_text semantics.
- Dedicated speech-to-expense service with separate confirmation UX — rejected; duplicates product surface and violates UX consistency.

---

## Decision 2: Gemini multimodal for speech (general model chain)

**Decision**: Add a Gemini client helper that sends audio bytes as `Part.from_bytes` with MIME `audio/mp4` or `audio/m4a` (LINE voice is m4a) plus a short “transcribe only” prompt. Use the **general** model fallback chain (same as text assist), **not** the receipt/Pro image chain. Meter as general/assist usage — never `receipt_analysis`.

**Rationale**: Project already uses Gemini multimodal for images; audio parts are supported by the same SDK pattern. Receipt metering must not apply to short voice clips. Spec assumes voice consumes normal AI-assisted inbound quota.

**Alternatives considered**:
- External STT (Whisper API, Cloud Speech) — rejected for v1; extra vendor/credential surface; Gemini already required for expense parsing.
- Client-side LINE speech recognition — rejected; not available as bot webhook text for hold-to-talk audio messages.

---

## Decision 3: Duration from LINE webhook; size after content fetch

**Decision**:
- Prefer LINE AudioMessage **`duration`** (milliseconds) from the webhook for the **60s** check **before** downloading content when present (`duration > 60000` → reject without fetch/LLM).
- Always enforce **5 MB** on downloaded byte length (`len(audio_bytes) > 5 * 1024 * 1024` → reject without LLM).
- If webhook duration is missing: still enforce size; optionally probe duration from bytes only if a lightweight library is already acceptable — **v1 default**: proceed when size OK and treat empty/failed transcription as unusable audio (spec allows size-only when duration unknown).
- Boundary: duration `<= 60000` ms and size `<= 5 MiB` accepted; strictly greater rejected.

**Rationale**: LINE documents `duration` in ms on audio message content; content download uses the same `get_message_content` blob API as images. Early reject minimizes abuse cost (FR-004–FR-006).

**Alternatives considered**:
- Always download then probe with ffprobe — heavier dependency; deferred unless webhook duration proves unreliable.
- Reject all audio missing duration — too harsh; harness and some edge payloads may omit it.

---

## Decision 4: Extend inbound retry schema for `audio`

**Decision**: Migration widens `inbound_messages.message_type` CHECK to include `'audio'`. Add `save_inbound_audio_message`. Extend message retry to re-fetch audio bytes and call `process_audio_message`. Add failure kind such as `audio_fetch_error` (or reuse a generic content-fetch error if already generalized).

**Rationale**: Text/image already persist inbound rows for retry; voice must not be a special case that cannot recover from transient Gemini/LINE failures.

**Alternatives considered**:
- No inbound row for audio — rejected; breaks retry feature parity and observability.
- Store raw audio in object storage — out of scope (spec: no long-term recording library).

---

## Decision 5: Localized over-limit / unusable replies via i18n stack

**Decision**: Add confirmation/persona i18n keys for: audio too long (state 60s), audio too large (state 5 MB), unusable/silent audio, and keep using existing unsupported/non-expense templates after transcription when applicable. Resolve language/persona with existing `resolve_tenant_reply_language` / `persona_scope`.

**Rationale**: Constitution UX consistency + AGENTS.md bot behavior settings require all user-facing text through the i18n/persona stack.

**Alternatives considered**:
- Hard-coded English strings — rejected by project rules.
- Reuse generic unsupported only — rejected; FR-006 requires naming the violated limit.

---

## Decision 6: Functional tests mock Gemini/LINE; no production ledger writes

**Decision**: Add `audio_message_event` webhook helper and `tests/functional/bot/test_voice_expense_flow.py` covering: successful confirm (mocked transcript + existing parse mocks), over-duration reject (no Gemini), over-size reject (no Gemini), unusable/empty transcript. Unit-test validators in isolation.

**Rationale**: FR-011 + constitution Test-First + feature 021 PR lane conventions.

**Alternatives considered**:
- Live LINE/Gemini E2E in CI — rejected; flaky and costly; contradicts 021 mocked lane.
- Harness-only manual verification — insufficient for merge gate.

---

## Decision 7: Architecture doc update at implement time

**Decision**: Implementation PR updates `docs/ARCHITECTURE.md` expense-capture / inbound message diagrams to include voice/audio alongside text and image. Plan-only artifacts do not change architecture prose yet (architecture-docs rule: Spec Kit planning alone is exempt until behavior ships).

**Rationale**: Voice is a new primary user-facing data flow; diagrams would otherwise mislead after merge of code.

**Alternatives considered**:
- Update architecture in the plan PR — optional; deferred to implement PR to avoid documenting unimplemented behavior as current state.
