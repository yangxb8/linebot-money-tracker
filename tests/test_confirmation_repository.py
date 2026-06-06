import os
import unittest
from unittest.mock import MagicMock, patch

from services.confirmation_repository import ConfirmationRecord, save_confirmation, try_mark_reply_processed
from services.message_context import ConfirmationItemSnapshot


class TestConfirmationRepository(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(os.environ, {}, clear=False)
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    @patch('services.confirmation_repository.is_supabase_configured', return_value=False)
    def test_save_skips_when_not_configured(self, _configured):
        items = [
            ConfirmationItemSnapshot(
                line_item_index=0,
                expense_id='e1',
                description='Coffee',
                amount=__import__('decimal').Decimal('450'),
                currency='JPY',
                category_guess_code='food.dining.cafe',
                category_alternatives=('unknown',),
            )
        ]
        result = save_confirmation('bot-1', 'user-1', 'text', items)
        self.assertIsNone(result)

    @patch('services.confirmation_repository.get_supabase_client')
    @patch('services.confirmation_repository.is_supabase_configured', return_value=True)
    def test_save_inserts_confirmation_and_links(self, _configured, get_client):
        table = MagicMock()
        insert = MagicMock()
        insert.execute.return_value = MagicMock(data=[{'id': 'c1'}])
        table.insert.return_value = insert

        client = MagicMock()
        client.table.return_value = table
        get_client.return_value = client

        items = [
            ConfirmationItemSnapshot(
                line_item_index=0,
                expense_id='e1',
                description='Coffee',
                amount=__import__('decimal').Decimal('450'),
                currency='JPY',
                category_guess_code='food.dining.cafe',
                category_alternatives=('unknown',),
            )
        ]
        confirmation_id = save_confirmation('bot-1', 'user-1', 'confirm text', items)
        self.assertIsNotNone(confirmation_id)
        self.assertEqual(client.table.call_count, 2)

    @patch('services.confirmation_repository.get_supabase_client')
    @patch('services.confirmation_repository.is_supabase_configured', return_value=True)
    def test_get_confirmation_by_bot_message_id(self, _configured, get_client):
        table = MagicMock()
        chain = MagicMock()
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(
            data=[
                {
                    'id': 'c1',
                    'bot_message_id': 'bot-1',
                    'line_user_id': 'user-1',
                    'confirmation_text': 'hello',
                    'items_snapshot': [{'line_item_index': 0, 'expense_id': 'e1'}],
                    'pending_action': None,
                }
            ]
        )
        table.select.return_value.eq.return_value.eq.return_value = chain
        client = MagicMock()
        client.table.return_value = table
        get_client.return_value = client

        record = __import__('services.confirmation_repository', fromlist=['get_confirmation_by_bot_message_id']).get_confirmation_by_bot_message_id(
            'bot-1', 'user-1'
        )
        self.assertIsInstance(record, ConfirmationRecord)
        self.assertEqual(record.bot_message_id, 'bot-1')

    @patch('services.confirmation_repository.get_supabase_client')
    @patch('services.confirmation_repository.is_supabase_configured', return_value=True)
    def test_try_mark_reply_processed_duplicate(self, _configured, get_client):
        table = MagicMock()
        select_chain = MagicMock()
        select_chain.limit.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=[{'user_reply_message_id': 'r1'}])
        table.select.return_value.eq.return_value.eq.return_value = select_chain
        client = MagicMock()
        client.table.return_value = table
        get_client.return_value = client

        allowed = try_mark_reply_processed('user-1', 'r1')
        self.assertFalse(allowed)


if __name__ == '__main__':
    unittest.main()
