import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.gemini_client import GeminiClient
from services.message_handler import _enrich_and_persist_items
from services.categorize import CategoryResultWithProvenance
from services.tenant_context import TenantContext
from services.message_context import MessageContext


class TestMessageHandlerItemMemory(unittest.IsolatedAsyncioTestCase):
    async def test_enrich_passes_memory_mode_item(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')
        context = MessageContext(
            tenant=tenant,
            source_message_id='msg-1',
            reply_language='ja',
        )

        with patch(
            'services.message_handler.classify_expense_with_memory',
            AsyncMock(
                return_value=CategoryResultWithProvenance(
                    guessed='food.grocery',
                    alternatives=(),
                    source='llm',
                    merchant_key='aeon',
                    display_merchant='イオン',
                    item_key='牛乳',
                )
            ),
        ) as classify_mock, patch(
            'services.message_handler.resolve_code',
            return_value=MagicMock(code='food.grocery', path_names=('食費', '食料品')),
        ), patch(
            'services.message_handler.format_category_path',
            return_value='食費 > 食料品',
        ), patch(
            'services.message_handler.insert_expenses',
            return_value=MagicMock(error=None, inserted=1, skipped=0),
        ), patch(
            'services.message_handler.format_expense_items',
            return_value='ok',
        ), patch(
            'services.message_handler._build_confirmation_payload',
            return_value=None,
        ), patch(
            'services.message_handler._confirmation_format_kwargs',
            return_value={},
        ), patch(
            'services.message_handler.build_insert_row',
            return_value=MagicMock(),
        ):
            await _enrich_and_persist_items(
                [{'description': '牛乳', 'amount': 198, 'currency': 'JPY', 'store_name': 'イオン'}],
                gemini,
                context,
                memory_mode='item',
            )

        self.assertEqual(classify_mock.await_args.kwargs.get('memory_mode'), 'item')

    async def test_enrich_default_memory_mode_merchant(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')
        context = MessageContext(
            tenant=tenant,
            source_message_id='msg-2',
            reply_language='ja',
        )

        with patch(
            'services.message_handler.classify_expense_with_memory',
            AsyncMock(
                return_value=CategoryResultWithProvenance(
                    guessed='food.dining',
                    alternatives=(),
                    source='memory',
                    merchant_key='starbucks',
                )
            ),
        ) as classify_mock, patch(
            'services.message_handler.resolve_code',
            return_value=MagicMock(code='food.dining', path_names=('食費', '外食')),
        ), patch(
            'services.message_handler.format_category_path',
            return_value='食費 > 外食',
        ), patch(
            'services.message_handler.insert_expenses',
            return_value=MagicMock(error=None, inserted=1, skipped=0),
        ), patch(
            'services.message_handler.format_expense_items',
            return_value='ok',
        ), patch(
            'services.message_handler._build_confirmation_payload',
            return_value=None,
        ), patch(
            'services.message_handler._confirmation_format_kwargs',
            return_value={},
        ), patch(
            'services.message_handler.build_insert_row',
            return_value=MagicMock(),
        ):
            await _enrich_and_persist_items(
                [{'description': 'スターバックス ラテ', 'amount': 580, 'currency': 'JPY'}],
                gemini,
                context,
            )

        self.assertEqual(classify_mock.await_args.kwargs.get('memory_mode'), 'merchant')


if __name__ == '__main__':
    unittest.main()
