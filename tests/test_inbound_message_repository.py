import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from services.inbound_message_repository import (
    INBOUND_MESSAGE_TTL_DAYS,
    FailureRetryAnchor,
    InboundMessageRecord,
    get_failure_retry_anchor,
    get_inbound_message,
    purge_expired_inbound_messages,
    save_failure_retry_anchor,
    save_inbound_text_message,
)
from services.tenant_context import TenantContext


class TestInboundMessageRepository(unittest.TestCase):
    def setUp(self):
        self.tenant = TenantContext.personal('user-1')

    @patch('services.inbound_message_repository.is_supabase_configured', return_value=True)
    @patch('services.inbound_message_repository.get_supabase_client')
    def test_save_inbound_text_message_purges_before_write(self, get_client, _configured):
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table
        table.delete.return_value = table
        table.lt.return_value = table
        table.upsert.return_value = table
        table.execute.return_value = MagicMock(data=[])
        get_client.return_value = client

        save_inbound_text_message(
            message_id='msg-1',
            line_user_id='user-1',
            tenant=self.tenant,
            text_content='Lunch 1200',
        )

        client.table.assert_any_call('inbound_messages')
        table.delete.assert_called_once()
        table.upsert.assert_called_once()

    @patch('services.inbound_message_repository.is_supabase_configured', return_value=True)
    @patch('services.inbound_message_repository.get_supabase_client')
    def test_get_inbound_message_returns_none_when_expired(self, get_client, _configured):
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table
        table.select.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        expired = datetime.now(timezone.utc) - timedelta(days=INBOUND_MESSAGE_TTL_DAYS + 1)
        table.execute.return_value = MagicMock(
            data=[
                {
                    'message_id': 'msg-1',
                    'line_user_id': 'user-1',
                    'tenant_type': 'user',
                    'tenant_id': 'user-1',
                    'message_type': 'text',
                    'text_content': 'Lunch 1200',
                    'created_at': expired.isoformat(),
                }
            ]
        )
        get_client.return_value = client

        self.assertIsNone(get_inbound_message('msg-1'))

    @patch('services.inbound_message_repository.is_supabase_configured', return_value=True)
    @patch('services.inbound_message_repository.get_supabase_client')
    def test_get_failure_retry_anchor(self, get_client, _configured):
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table
        table.select.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.return_value = MagicMock(
            data=[
                {
                    'bot_error_message_id': 'bot-error-1',
                    'original_message_id': 'msg-1',
                    'original_line_user_id': 'user-1',
                    'tenant_type': 'user',
                    'tenant_id': 'user-1',
                    'failure_kind': 'processing_error',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                }
            ]
        )
        get_client.return_value = client

        anchor = get_failure_retry_anchor('bot-error-1', self.tenant)
        self.assertIsInstance(anchor, FailureRetryAnchor)
        self.assertEqual(anchor.original_message_id, 'msg-1')

    @patch('services.inbound_message_repository.is_supabase_configured', return_value=False)
    def test_noop_when_supabase_not_configured(self, _configured):
        purge_expired_inbound_messages()
        save_failure_retry_anchor(
            bot_error_message_id='bot-1',
            original_message_id='msg-1',
            original_line_user_id='user-1',
            tenant=self.tenant,
            failure_kind='processing_error',
        )
        self.assertIsNone(get_inbound_message('msg-1'))


if __name__ == '__main__':
    unittest.main()
