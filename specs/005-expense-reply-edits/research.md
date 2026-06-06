# Research: Expense Reply Edits

**Feature**: 005-expense-reply-edits  
**Date**: 2026-06-06

## R1: LINE reply-to-message identification

**Decision**: Use inbound `quotedMessageId` on text messages to identify which bot confirmation the user replied to; persist outbound bot message ID from `ReplyMessageResponse.sent_messages[0].id` when sending expense confirmations.

**Rationale**: LINE Messaging API exposes `quotedMessageId` on webhook text events when the user uses the Reply action. The Reply API response includes `SentMessage` objects with `id` — these IDs are what users quote on follow-up replies. This matches FR-001/FR-002 without custom correlation tokens in message text.

**Alternatives considered**:
- Embed hidden correlation UUID in confirmation text — fragile, poor UX, user-visible.
- Match by reply text snapshot fuzzy search — unreliable for edits.
- Use `quoteToken` only — tokens expire; message IDs are durable for linkage.

**Implementation note**: Extend `line_event.extract_quoted_message_id(event)` reading `message.quoted_message_id` (line-bot-sdk v3 attribute naming). Wrap `reply_message` in helper that returns `(reply_text, sent_message_id)`.

---

## R2: Confirmation persistence shape

**Decision**: Table `confirmation_messages` keyed by `bot_message_id` (TEXT, UNIQUE) with JSONB `items_snapshot` capturing per-line-item metadata including numbered category alternatives; junction table `confirmation_expenses` linking confirmation → `expenses.id`.

**Rationale**: FR-006 requires mapping bare `1`–`3` to alternatives from the **specific confirmation sent**, not re-inferring from taxonomy. JSONB snapshot avoids re-parsing formatted text. Junction supports multi-item and per-item restore/delete.

**Alternatives considered**:
- Store only expense IDs and re-fetch current category — loses original alternative list for numbered picks.
- Single JSON blob without normalization — harder to query audit joins.

---

## R3: Soft delete representation

**Decision**: Add nullable `deleted_at TIMESTAMPTZ` on `expenses`. Active = `deleted_at IS NULL`. Restore = set `deleted_at` to NULL. No hard delete in v1.

**Rationale**: Clarification Q1 + restore/restore-all. Minimal schema change; audit row retained. Update `monthly_expense_total` / `yearly_expense_total` to filter `deleted_at IS NULL`.

**Alternatives considered**:
- `is_deleted` boolean — equivalent; timestamp adds audit value.
- Separate `deleted_expenses` table — more joins; rejected for scope.

---

## R4: Delete-all confirmation state

**Decision**: Column `pending_action` on `confirmation_messages` (`NULL | 'delete_all'`) set when user requests bulk delete; cleared after YES executes or on unrelated edit intent. User confirmation detected by intent JSON `{action: "confirm_pending"}` when `pending_action = 'delete_all'` and text matches affirmative (YES/はい/是).

**Rationale**: Clarification Q3 — confirm before bulk soft-delete without a separate state machine service. Same confirmation thread; user still replies to same bot message.

**Alternatives considered**:
- Separate `pending_actions` table — over-engineered for one pending type in v1.
- Immediate delete-all — rejected by spec.

---

## R5: LLM edit intent vs free-form summary

**Decision**: Gemini returns **structured JSON only** for edit parsing (`reply_edit.py`); action summary text generated in Python (`reply_summary.py`) using detected reply language (JP/EN/ZH heuristics + intent metadata).

**Rationale**: Extends 004 llm-db-boundary pattern. Summaries must be deterministic and testable (SC-003). LLM handles ambiguous natural language; app validates and applies.

**Alternatives considered**:
- LLM writes user-facing summary — harder to test, inconsistent formatting.
- Regex-only parsing — insufficient for JP/EN/ZH free text (FR-015).

---

## R6: Reply edit idempotency

**Decision**: Table `processed_reply_messages` with UNIQUE `(line_user_id, user_reply_message_id)` inserted before applying mutations; duplicate webhook → skip apply, return prior summary stub or "already processed" message.

**Rationale**: FR-011 mirrors 004 insert idempotency pattern.

---

## R7: Console harness reply simulation

**Decision**: `local_run.py --reply-to <bot_message_id> --text "..."` builds `ReplyContext` with synthetic user reply message UUID; confirmations saved with console-prefixed bot message IDs from uuid4.

**Rationale**: FR/console edge case in spec; enables pytest and manual QA without LINE reply UI.

---

## R8: Multilingual reply detection

**Decision**: Simple heuristic: CJK unified ideographs without kana → Chinese; hiragana/katakana present → Japanese; else English. Fallback Japanese for summaries per FR-015.

**Rationale**: Good enough for v1; avoids extra LLM call for language ID.

**Alternatives considered**:
- LLM `detected_language` field in intent JSON — optional future enhancement.
