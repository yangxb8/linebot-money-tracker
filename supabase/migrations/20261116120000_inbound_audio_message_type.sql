-- Feature 022: allow audio inbound messages + audio fetch failure kind

ALTER TABLE inbound_messages
    DROP CONSTRAINT IF EXISTS inbound_messages_message_type_check;

ALTER TABLE inbound_messages
    ADD CONSTRAINT inbound_messages_message_type_check
    CHECK (message_type IN ('text', 'image', 'audio'));

ALTER TABLE failure_retry_anchors
    DROP CONSTRAINT IF EXISTS failure_retry_anchors_failure_kind_check;

ALTER TABLE failure_retry_anchors
    ADD CONSTRAINT failure_retry_anchors_failure_kind_check
    CHECK (failure_kind IN ('processing_error', 'image_fetch_error', 'audio_fetch_error'));
