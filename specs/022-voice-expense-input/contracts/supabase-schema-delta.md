# Supabase Schema Delta: Inbound Audio

**Feature**: 022-voice-expense-input  
**Migration**: `supabase/migrations/YYYYMMDDHHMMSS_inbound_audio_message_type.sql`

## Change summary

Widen `inbound_messages.message_type` (and related failure-kind constraints if present) so audio messages can be stored and retried like text/image.

## DDL sketch

Exact prior constraint names come from `supabase/migrations/20260618120000_message_retry.sql` — drop/replace CHECK accordingly:

```sql
-- Example shape (adjust to actual constraint names)
ALTER TABLE inbound_messages
  DROP CONSTRAINT IF EXISTS inbound_messages_message_type_check;

ALTER TABLE inbound_messages
  ADD CONSTRAINT inbound_messages_message_type_check
  CHECK (message_type IN ('text', 'image', 'audio'));

-- If failure_kind is constrained, extend similarly, e.g.:
-- CHECK (failure_kind IS NULL OR failure_kind IN (
--   'processing_error', 'image_fetch_error', 'audio_fetch_error'
-- ))
```

## RLS / grants

No change to RLS posture: inbound messages remain backend/service-role only (bot). Web dashboard does not read raw inbound audio rows for v1.

## Data backfill

None. Existing rows remain `text` / `image`.

## Verification

```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'inbound_messages'::regclass
  AND contype = 'c';
```

Confirm `audio` appears in the `message_type` check definition.
