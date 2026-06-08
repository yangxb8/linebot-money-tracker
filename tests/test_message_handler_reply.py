"""Reply-edit handler integration tests (feature 005)."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.gemini_client import GeminiClient
from services.message_context import MessageContext, ReplyContext
from services.tenant_context import TenantContext
from services.message_handler import format_expense_items, process_reply_edit, process_text_message


class TestMessageHandlerReply(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_confirmation_guidance(self):
        gemini = MagicMock(spec=GeminiClient)
        ctx = ReplyContext(
            tenant=TenantContext.personal('u1'),
            user_reply_message_id='r1',
            quoted_bot_message_id='missing',
        )
        with patch('services.message_handler.try_mark_reply_processed', return_value=True), patch(
            'services.message_handler.get_confirmation_by_bot_message_id', return_value=None
        ):
            result = await process_reply_edit('2', ctx, gemini)
        self.assertIn('confirmation', result.text.lower())

    def test_group_confirmation_includes_logged_by(self):
        text = format_expense_items(
            [{'description': 'Coffee', 'amount': 450, 'currency': 'JPY'}],
            logged_by_line_user_id='user-a',
            is_shared_tenant=True,
        )
        self.assertIn('Logged by: user-a', text)

    def test_personal_confirmation_omits_logged_by(self):
        text = format_expense_items(
            [{'description': 'Coffee', 'amount': 450, 'currency': 'JPY'}],
            logged_by_line_user_id='user-a',
            is_shared_tenant=False,
        )
        self.assertNotIn('Logged by:', text or '')

    async def test_confirmation_footer_updated(self):
        text = format_expense_items(
            [
                {
                    'description': 'Coffee',
                    'amount': 450,
                    'currency': 'JPY',
                    'category_guess_path': 'Food',
                    'category_alternative_paths': ['Alt1'],
                }
            ]
        )
        self.assertIn('Reply to this message', text)

    @patch('services.message_handler.fetch_expense_ids_for_message', return_value=[{'id': 'e1', 'line_item_index': 0}])
    async def test_process_text_returns_confirmation_payload(self, _fetch):
        gemini = MagicMock(spec=GeminiClient)
        context = MessageContext(tenant=TenantContext.personal('u1'), source_message_id='m1')
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=True)), patch(
            'services.message_handler.parse_text_for_expenses',
            return_value=[{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}],
        ), patch(
            'services.message_handler.classify_expense',
            AsyncMock(return_value=__import__('services.categorize', fromlist=['CategoryResult']).CategoryResult(
                guessed='unknown', alternatives=('food.dining',)
            )),
        ), patch(
            'services.message_handler.insert_expenses',
            return_value=__import__('services.expense_repository', fromlist=['PersistResult']).PersistResult(
                inserted=1, skipped=0
            ),
        ):
            bot_reply = await process_text_message('Lunch 120 THB', gemini, context)
        self.assertIsNotNone(bot_reply.confirmation)
        self.assertEqual(bot_reply.confirmation.items[0].expense_id, 'e1')


if __name__ == '__main__':
    unittest.main()
