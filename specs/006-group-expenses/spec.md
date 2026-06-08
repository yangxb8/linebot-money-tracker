# Feature Specification: Group Shared Expenses

**Feature Branch**: `006-group-expenses`

**Created**: 2026-06-08

**Status**: Draft

**Input**: When the bot is added to a LINE group (or multi-person room), all members share one expense ledger keyed by the chat, instead of per-user isolation.

## Clarifications

### Session 2026-06-08

- Q: Personal 1:1 chats — should they keep working as today? → A: **Dual mode** — 1:1 = personal (`line_user_id`); group/room = shared (`groupId`/`roomId`).
- Q: Who can reply-edit expenses logged by another group member? → A: **Any group member** may edit; `reply_edit_audit` records who performed the edit.
- Q: Should expenses record who logged them? → A: **Store submitter** (`logged_by_line_user_id`); show attribution in group confirmation text.
- Q: LINE multi-person rooms (`source.type = room`) — include them? → A: **Yes** — treat `room` the same as `group` (shared ledger per room ID).
- Q: What should the bot show in group confirmation replies beyond item details? → A: **Items only** — same item/category format as 1:1; no group monthly totals.

## Out of Scope (this feature)

- Split bills / per-member expense shares
- Settlement / balance tracking
- Invite-based households independent of LINE chats
- Per-member filtering commands
- Group admin roles or membership management
- LINE profile display names (attribution uses LINE user ID substring)

## User Scenarios & Testing

### User Story 1 - Shared ledger in group chats (Priority: P1)

When the bot receives an expense message in a LINE group or room, the expense is stored under that chat's ID so all members share the same ledger. 1:1 DMs continue to use the sender's personal ledger.

**Acceptance Scenarios**:

1. **Given** a user sends an expense in a 1:1 DM, **When** processing completes, **Then** expenses are stored with `tenant_type=user` and `tenant_id` equal to the sender's LINE user ID.
2. **Given** user A sends an expense in a LINE group, **When** processing completes, **Then** expenses are stored with `tenant_type=group` and `tenant_id` equal to the group's LINE group ID, with `logged_by_line_user_id` set to user A.
3. **Given** user B sends an expense in the same group, **When** processing completes, **Then** expenses share the same `tenant_id` as user A's group expenses.
4. **Given** a user sends an expense in a LINE room, **When** processing completes, **Then** expenses use `tenant_type=room` and the room ID as `tenant_id`.

---

### User Story 2 - Group reply-edits by any member (Priority: P1)

Any member of a group may reply to a bot confirmation to edit or delete expenses logged by another member. The audit log records which member performed the edit.

**Acceptance Scenarios**:

1. **Given** user A logged an expense in a group and received a confirmation, **When** user B replies to that confirmation to change the amount, **Then** the expense is updated and `reply_edit_audit.line_user_id` records user B.
2. **Given** user B attempts a reply-edit in a group they are not part of (different tenant), **Then** the confirmation is not found and the user receives the unknown-confirmation message.

---

### User Story 3 - Group confirmation attribution (Priority: P2)

Group confirmations include who logged the expense. Item lines and category prompts match the 1:1 format; no group rollup totals are shown.

**Acceptance Scenarios**:

1. **Given** a group expense is logged, **When** the confirmation is sent, **Then** the reply includes a `Logged by:` line with the submitter's LINE user ID and the same per-item format as 1:1.
2. **Given** a 1:1 expense is logged, **When** the confirmation is sent, **Then** no `Logged by:` line is shown.

---

## Requirements

### Functional Requirements

- **FR-001**: The system MUST resolve expense tenant from LINE `source.type`: `user` → personal ledger; `group` → `source.groupId`; `room` → `source.roomId`.
- **FR-002**: Each stored expense MUST include `tenant_type`, `tenant_id`, and `logged_by_line_user_id`.
- **FR-003**: Expense idempotency MUST be scoped to `(tenant_type, tenant_id, source_message_id, line_item_index)`.
- **FR-004**: Confirmation linkage MUST be scoped to `(tenant_type, tenant_id, bot_message_id)`.
- **FR-005**: Any member of a group/room tenant MUST be able to reply-edit confirmations in that chat; audit MUST record the editing user's LINE ID.
- **FR-006**: Group/room confirmation replies MUST include submitter attribution; MUST NOT include group monthly totals.
- **FR-007**: Rollup RPCs MUST filter by `tenant_type` and `tenant_id`.
- **FR-008**: Existing personal expenses MUST be backfilled as `tenant_type=user`, `tenant_id=line_user_id`.

### Edge Cases

- Group message without `groupId` or room without `roomId`: reject or fall back to personal tenant (implementation: require chat ID; skip tenant resolution if missing).
- Bot added to group but sender `user_id` missing: cannot attribute submitter; skip processing.
- Webhook retry in group: idempotent on tenant-scoped message key.
