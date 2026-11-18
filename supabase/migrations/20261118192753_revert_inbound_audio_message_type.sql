-- Forward rollback of live migration 20261116092639_inbound_audio_message_type
-- (repo file from PR #101 was 20261116120000_inbound_audio_message_type.sql; removed by #106).
-- Restores pre-audio CHECK constraints from 20260618120000_message_retry.sql.
--
-- Data handling (scoped to the removed audio path only):
--   1) Drop any audio_fetch_error retry anchors.
--   2) Drop inbound_messages with message_type='audio'.
--      failure_retry_anchors.original_message_id REFERENCES inbound_messages
--      ON DELETE CASCADE, so anchors pointing at those audio rows are removed too.
-- Non-audio inbound messages and unrelated household ledger rows are not touched.

DELETE FROM failure_retry_anchors
WHERE failure_kind = 'audio_fetch_error';

DELETE FROM inbound_messages
WHERE message_type = 'audio';

ALTER TABLE inbound_messages
    DROP CONSTRAINT IF EXISTS inbound_messages_message_type_check;

ALTER TABLE inbound_messages
    ADD CONSTRAINT inbound_messages_message_type_check
    CHECK (message_type IN ('text', 'image'));

ALTER TABLE failure_retry_anchors
    DROP CONSTRAINT IF EXISTS failure_retry_anchors_failure_kind_check;

ALTER TABLE failure_retry_anchors
    ADD CONSTRAINT failure_retry_anchors_failure_kind_check
    CHECK (failure_kind IN ('processing_error', 'image_fetch_error'));
