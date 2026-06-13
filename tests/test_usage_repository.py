import unittest
from unittest.mock import MagicMock, patch

from services.usage_repository import record_llm_usage


class TestUsageRepository(unittest.TestCase):
    @patch('services.usage_repository.is_usage_tracking_enabled', return_value=True)
    @patch('services.usage_repository.get_user_usage_snapshot')
    @patch('services.usage_repository.get_supabase_client')
    def test_record_llm_usage_idempotent(self, client_mock, snapshot_mock, _enabled):
        client = MagicMock()
        client_mock.return_value = client
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'id': 'existing'}]
        )

        recorded = record_llm_usage(
            charged_line_user_id='u1',
            sender_line_user_id='u1',
            operation_type='intent',
            operation_label='text',
            source_message_id='msg-1',
            tenant_type='user',
            tenant_id='u1',
            pooled=False,
        )
        self.assertFalse(recorded)
        snapshot_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
