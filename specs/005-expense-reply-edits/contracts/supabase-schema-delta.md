# Contract: Supabase Schema Delta

**Feature**: 005-expense-reply-edits  
**Migration**: `supabase/migrations/20260606130000_expense_reply_edits.sql`

## Alters

### expenses

| Change | Detail |
| ------ | ------ |
| ADD `deleted_at` | timestamptz NULL |
| ADD `updated_at` | timestamptz NOT NULL DEFAULT now() |
| INDEX | `(line_user_id, deleted_at)` partial WHERE deleted_at IS NULL optional |

### RPC functions (replace)

Both `monthly_expense_total` and `yearly_expense_total` add filter:

```sql
AND e.deleted_at IS NULL
```

## Creates

| Table | Purpose |
| ----- | ------- |
| `confirmation_messages` | Bot confirmation linkage |
| `confirmation_expenses` | Confirmation ↔ expense junction |
| `reply_edit_audit` | FR-014 audit trail |
| `processed_reply_messages` | Reply idempotency |

## RLS

Enable RLS on new user-scoped tables; no anon/authenticated policies (service role bot access), consistent with 004.

## Apply

Same methods as 004: MCP `apply_migration`, Dashboard SQL, or Supabase CLI.
