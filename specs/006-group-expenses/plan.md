# Implementation Plan: Group Shared Expenses

**Branch**: `cursor/group-expenses-1f83` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)

## Summary

Introduce **tenant-scoped expense ledgers**: personal 1:1 chats keep `tenant_type=user`; LINE groups and rooms use `tenant_type=group|room` with the chat ID as `tenant_id`. All repositories, confirmations, reply-edits, and rollup RPCs switch from `line_user_id`-only scoping to `(tenant_type, tenant_id)`. Group confirmations add a `Logged by:` attribution line; any member may reply-edit with audit attribution.

## Technical Context

**Storage**: Supabase migration adding `tenant_type`, `tenant_id`, `logged_by_line_user_id` to `expenses`, `confirmation_messages`, `processed_reply_messages`; update unique constraints and rollup RPCs.

**LINE**: Extend `line_event.py` to extract `source.type`, `groupId`, `roomId`; new `tenant_context.py` resolves `TenantContext`.

## Architecture

```text
LINE event → resolve TenantContext → MessageContext / ReplyContext
         → expense_repository (tenant-scoped insert/query)
         → confirmation_repository (tenant-scoped save/load)
         → reply_edit (any member; audit editor line_user_id)
```

## Source Changes

| File | Change |
|------|--------|
| `services/tenant_context.py` | NEW: `TenantContext`, `resolve_tenant_from_event` |
| `services/message_context.py` | Add `tenant` to contexts |
| `services/line_event.py` | Extract group/room/source type |
| `services/expense_repository.py` | Tenant columns; upsert on tenant key |
| `services/confirmation_repository.py` | Tenant-scoped save/load/idempotency |
| `services/message_handler.py` | Group attribution in confirmation; tenant in payloads |
| `main.py` / `local_run.py` | Resolve tenant; `--group-id` / `--room-id` flags |
| `supabase/migrations/20260608120000_group_expenses.sql` | Schema delta |

## Migration Strategy

1. Add nullable tenant columns + backfill from `line_user_id`
2. Set NOT NULL; replace unique constraint on expenses
3. Update rollup RPCs to filter by tenant
4. Keep `line_user_id` populated as `logged_by_line_user_id` for backward-compatible reads
