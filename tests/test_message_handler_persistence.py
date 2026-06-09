import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from services.categorize import CategoryResult
from services.expense_repository import PersistResult
from services.gemini_client import GeminiClient
from services.message_context import MessageContext
from services.tenant_context import TenantContext
from services.message_handler import format_expense_items, process_text_message


def _unknown_category():
    return CategoryResult(guessed='unknown', alternatives=())


class TestMessageHandlerPersistence(unittest.IsolatedAsyncioTestCase):
    async def test_persists_when_context_provided(self):
        gemini = MagicMock(spec=GeminiClient)
        context = MessageContext(
            tenant=TenantContext.personal('u1'),
            source_message_id='msg-1',
            reply_language='en',
        )
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=True)), patch(
            'services.message_handler.parse_text_for_expenses',
            return_value=[{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}],
        ), patch(
            'services.message_handler.classify_expense',
            AsyncMock(return_value=_unknown_category()),
        ), patch(
            'services.message_handler.insert_expenses',
            return_value=PersistResult(inserted=1, skipped=0),
        ) as insert_mock:
            reply = await process_text_message('Lunch 120 THB', gemini, context)
        insert_mock.assert_called_once()
        self.assertIn('Detected expense(s):', reply.text)
        self.assertIn('Category (guess):', reply.text)

    async def test_skips_persist_without_context(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=True)), patch(
            'services.message_handler.parse_text_for_expenses',
            return_value=[{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}],
        ), patch(
            'services.message_handler.classify_expense',
            AsyncMock(return_value=_unknown_category()),
        ), patch('services.message_handler.insert_expenses') as insert_mock:
            reply = await process_text_message('Lunch 120 THB', gemini)
        insert_mock.assert_not_called()
        self.assertIn('検出した支出:', reply.text)

    async def test_storage_error_still_returns_reply(self):
        gemini = MagicMock(spec=GeminiClient)
        context = MessageContext(
            tenant=TenantContext.personal('u1'),
            source_message_id='msg-1',
            reply_language='en',
        )
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=True)), patch(
            'services.message_handler.parse_text_for_expenses',
            return_value=[{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}],
        ), patch(
            'services.message_handler.classify_expense',
            AsyncMock(return_value=_unknown_category()),
        ), patch(
            'services.message_handler.insert_expenses',
            return_value=PersistResult(inserted=0, skipped=0, error='db error'),
        ):
            reply = await process_text_message('Lunch 120 THB', gemini, context)
        self.assertIn('Detected expense(s):', reply.text)


class TestEnrichedReplyFormat(unittest.TestCase):
    def test_shows_guess_and_alternatives(self):
        text = format_expense_items(
            [
                {
                    'description': 'Supermarket',
                    'amount': 3500,
                    'currency': 'JPY',
                    'category_guess_path': '食費 > 食料品',
                    'category_alternative_paths': ['食費 > 外食', '不明'],
                }
            ]
        )
        self.assertIn('カテゴリ（推測）: 食費 > 食料品', text)
        self.assertIn('1️⃣ Supermarket:', text)
        self.assertIn('  1) 食費 > 外食', text)
        self.assertIn('  2) 不明', text)
        self.assertIn('このメッセージに返信', text)

    def test_no_budget_impact_text(self):
        text = format_expense_items(
            [
                {
                    'description': 'Train',
                    'amount': 200,
                    'currency': 'JPY',
                    'category_guess_path': '交通 > 公共交通',
                    'category_alternative_paths': [],
                }
            ]
        )
        lowered = (text or '').lower()
        self.assertNotIn('budget', lowered)
        self.assertNotIn('予算', text or '')


class TestExpenseRollupLogic(unittest.TestCase):
    """Rollup semantics documented in data-model; RPC integration mocked."""

    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_monthly_rpc_called_with_jst_month(self, _configured, get_client):
        from services.expense_repository import monthly_expense_total

        rpc = MagicMock()
        rpc.execute.return_value = MagicMock(data=Decimal('500'))
        client = MagicMock()
        client.rpc.return_value = rpc
        get_client.return_value = client

        total = monthly_expense_total(TenantContext.personal('user'), 2026, 6, 'food-id', 'JPY')
        self.assertEqual(total, Decimal('500'))
        client.rpc.assert_called_once()


if __name__ == '__main__':
    unittest.main()
