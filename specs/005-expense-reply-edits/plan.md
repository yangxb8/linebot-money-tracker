# Implementation Plan: Expense Reply Edits

**Branch**: `005-expense-reply-edits` | **Date**: 2026-06-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification + clarifications (soft delete/restore, multi-item numbered picks, delete-all confirm, JP/EN/ZH, restore-all). Builds on **004-supabase-expense-storage**.

**User direction**: After expense confirmation, LINE users **reply to the bot message** to edit or soft-delete expenses. **LLM produces JSON edit intents only** — app executes **predefined repository mutations**, never LLM-generated SQL.

## Summary

Extend the expense logging pipeline to **persist confirmation message linkage** (bot outbound message ID + text snapshot + per-item category alternatives), detect **user reply-to-message** via LINE `quotedMessageId`, interpret replies with **Gemini JSON** (JP/EN/ZH), and apply **fixed Supabase updates** (field edits, soft-delete, restore, delete-all with pending confirmation). Bot returns a **language-matched action summary**. Rollup RPCs updated to exclude soft-deleted rows.

## Technical Context

**Language/Version**: Python 3.11+ (3.13 in CI)

**Primary Dependencies**: FastAPI, line-bot-sdk, google-genai, supabase, jsonschema, pytest (unchanged from 004)

**Storage**: Supabase Postgres (`https://nyuenufldaqsjybjhawl.supabase.co`) — migration delta on `expenses` + new tables `confirmation_messages`, `reply_edit_audit`, `processed_reply_messages`

**Testing**: pytest with mocked Supabase + Gemini; JSON schema tests for edit intents; handler tests for reply routing, idempotency, delete-all confirm, restore-all

**Target Platform**: Google Cloud Run + local console harness (`local_run.py --reply-to`)

**Project Type**: web-service + CLI dev harness

**Performance Goals**: Reply-edit path adds ≤3s p95 (LLM intent + 1–N fixed DB updates); confirmation save adds ≤200ms after existing log flow

**Constraints**:
- **LLM never touches database** — JSON edit intent in, validated, repository mutations out ([contracts/llm-reply-edit-boundary.md](./contracts/llm-reply-edit-boundary.md))
- Reply must target stored confirmation (`quotedMessageId` / console `--reply-to`)
- Soft-deleted rows excluded from rollup RPCs
- Idempotent on user reply message ID (FR-011)
- Storage failure on edit must not crash webhook; user gets friendly error (FR-009/Story 5)
- JST for date corrections (FR-012)

**Scale/Scope**: One confirmation → 1–20 expenses typical; pending delete-all state on confirmation row; audit log append-only

## Architecture

```text
┌──────────────┐  log + confirm   ┌─────────────────────┐  save linkage   ┌──────────┐
│ User expense │ ───────────────► │ message_handler     │ ───────────────► │ Supabase │
│ message      │                  │ (detect→categorize→ │                 │ confirm  │
└──────────────┘                  │  insert→format)     │                 │ + expenses│
                                  └──────────┬──────────┘                 └──────────┘
                                             │ capture bot SentMessage.id
                                             ▼
┌──────────────┐  quotedMessageId ┌─────────────────────┐  fixed UPDATE   ┌──────────┐
│ User reply   │ ───────────────► │ reply_edit pipeline │ ───────────────► │ Supabase │
│ to confirm   │                  │ parse intent (JSON) │                 │ expenses │
└──────────────┘                  │ apply + summarize   │                 └──────────┘
                                  └─────────────────────┘
```

### Request routing (`main.py` / `message_handler`)

1. Extract `quoted_message_id` from inbound text event.
2. If present → `process_reply_edit(...)` (this feature).
3. Else → existing `process_text_message` / `process_image_message`; after LINE `reply_message`, persist confirmation via `confirmation_repository.save_confirmation(sent_message_id, ...)`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
| --------- | ---------- |
| Code Quality & Maintainability | Separate `confirmation_repository`, `reply_edit`, `reply_summary`; extend `expense_repository` with named mutators only |
| Test-First Delivery | Tests for JSON intent schema, soft-delete filter in RPCs, reply routing, idempotency, multilingual summaries |
| User Experience Consistency | Deterministic summary templates; clarification prompts for ambiguous multi-item |
| Performance & Reliability | Non-blocking edit failures; pending delete-all state machine on confirmation row |
| Observability & Feedback | `reply_edit_audit` + structured logs for intent/apply results |
| Secrets | Unchanged — service role server-only |

**Post-design re-check**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/005-expense-reply-edits/
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── llm-reply-edit-boundary.md
    ├── confirmation-linkage.md
    ├── reply-edit-intent.md
    ├── expense-mutation.md
    └── supabase-schema-delta.md
```

### Source Code (repository root)

```text
services/
  message_handler.py           # route: log flow vs reply-edit flow
  confirmation_repository.py   # save/load confirmation + pending_action
  reply_edit.py                  # LLM → EditIntent JSON; orchestrate apply
  reply_summary.py               # format action summary (JP/EN/ZH detect)
  expense_repository.py          # + update_expense, soft_delete, restore, ...
  line_event.py                  # + extract_quoted_message_id
  message_context.py             # + ReplyContext (quoted id, user reply id)
supabase/migrations/
  20260606130000_expense_reply_edits.sql
tests/
  test_reply_edit.py
  test_confirmation_repository.py
  test_message_handler_reply.py
  test_expense_repository_mutations.py
main.py                        # capture SentMessage.id; pass ReplyContext
local_run.py                   # --reply-to CONFIRMATION_ID
```

**Structure Decision**: Single Python service layout (same as 004); new modules alongside existing repositories.

## Implementation Approach

### Phase A — Schema & linkage (blocking)

1. Migration: `deleted_at` on `expenses`; new tables; patch rollup RPCs (`deleted_at IS NULL`).
2. `confirmation_repository.save_confirmation` after successful expense log + LINE reply send.
3. `line_event.extract_quoted_message_id` + `ReplyContext`.

### Phase B — Reply edit core (MVP)

4. `reply_edit.parse_edit_intent` — Gemini JSON + jsonschema ([reply-edit-intent.md](./contracts/reply-edit-intent.md)).
5. `expense_repository` mutators: `update_expense_fields`, `soft_delete_expenses`, `restore_expenses` (by expense UUID list).
6. Apply rules: single-item bare `1`–`3` → category alt; multi-item requires item ref; delete-all → set `pending_action`; YES → bulk soft-delete; restore-all immediate.
7. `reply_summary.format_edit_result` — before/after + language match.

### Phase C — Integration & polish

8. Wire `main.py` reply routing + capture sent message ID from `ReplyMessageResponse`.
9. `local_run.py --reply-to` for console testing.
10. Audit log writes on every processed reply.

## Complexity Tracking

No constitution violations requiring justification.

## Generated Artifacts

| Artifact | Path |
| -------- | ---- |
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Quickstart | [quickstart.md](./quickstart.md) |
| Contracts | [contracts/](./contracts/) |

**Next command**: `/speckit-tasks`
