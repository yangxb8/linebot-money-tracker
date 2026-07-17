import os
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from services.ai_assist import ReceiptImageParseResult
from services.categorize import CategoryResult, CategoryResultWithProvenance
from services.gemini_client import GeminiClient, GeminiUsageLimitError
from services.message_context import MessageContext
from services.message_handler import (
    canned_unsupported_reply,
    error_reply_text,
    receipt_parse_error_reply,
    usage_limit_reply,
    format_expense_items,
    process_image_message,
    process_text_message,
)
from services.tenant_context import TenantContext


class TestFormatExpenseItems(unittest.TestCase):
    def test_formats_single_item(self):
        text = format_expense_items(
            [{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}],
            language='en',
        )
        self.assertIn('✅ Lunch', text)
        self.assertIn('120', text)


class TestMessageHandlerAsync(unittest.IsolatedAsyncioTestCase):
    def _english_context(self):
        return MessageContext(
            tenant=TenantContext.personal('u1'),
            source_message_id='m1',
            reply_language='en',
        )

    def _patch_categorize(self):
        return patch(
            'services.message_handler.classify_expense_with_memory',
            AsyncMock(
                return_value=CategoryResultWithProvenance(
                    guessed='unknown',
                    alternatives=(),
                    source='llm',
                )
            ),
        )

    def _valid_llm_parse(self, items, total, store_name=None):
        return ReceiptImageParseResult(
            items=items,
            total=Decimal(str(total)),
            currency='JPY',
            store_name=store_name,
        )

    async def test_process_text_expense_with_parser(self):
        gemini = MagicMock(spec=GeminiClient)
        with self._patch_categorize(), patch('services.message_handler.classify_text_message_intent', AsyncMock(return_value='expense')), patch(
            'services.message_handler.parse_text_for_expenses',
            return_value=[{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}],
        ), patch('services.message_handler.insert_expenses'):
            reply = await process_text_message('Lunch 120 THB', gemini, self._english_context())
        self.assertIn('✅ Lunch', reply.text)
        gemini.generate_reply.assert_not_called()

    async def test_process_text_non_expense(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.classify_text_message_intent', AsyncMock(return_value='other')):
            reply = await process_text_message('Hello bot', gemini, self._english_context())
        self.assertIn(canned_unsupported_reply('en'), reply.text)
        self.assertIn('🐰', reply.text)

    async def test_process_text_persona_lookup_failure_falls_back(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch(
            'services.bot_persona.resolve_persona_for_tenant',
            side_effect=RuntimeError('fail'),
        ), patch('services.message_handler.classify_text_message_intent', AsyncMock(return_value='other')):
            reply = await process_text_message('Hello bot', gemini, self._english_context())
        self.assertIn('🐰', reply.text)
        self.assertIn('expense', reply.text.lower())

    async def test_process_text_uses_group_tenant_for_persona_lookup(self):
        gemini = MagicMock(spec=GeminiClient)
        context = MessageContext(
            tenant=TenantContext.group('g1', 'u1'),
            source_message_id='m1',
            reply_language='en',
        )
        with patch('services.message_handler.classify_text_message_intent', AsyncMock(return_value='other')        ), patch('services.message_handler.resolve_persona_for_tenant') as resolve_mock:
            from services.bot_persona import PersonaConfig

            resolve_mock.return_value = PersonaConfig(emoji_level=0)
            reply = await process_text_message('Hello bot', gemini, context)
        resolve_mock.assert_called_once()
        called_tenant = resolve_mock.call_args.args[0]
        self.assertEqual(called_tenant.tenant_type, 'group')
        self.assertEqual(called_tenant.tenant_id, 'g1')
        self.assertIn('🐰', reply.text)

    async def test_process_text_webapp_obvious_skips_intent_llm(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.parse_text_for_expenses', return_value=[]), patch(
            'services.message_handler.classify_text_message_intent', AsyncMock(return_value='expense')
        ) as intent_mock:
            reply = await process_text_message('网页', gemini, self._english_context())
        intent_mock.assert_not_awaited()
        self.assertIn('available', reply.text.lower())

    async def test_process_text_webapp_request_via_combined_intent(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.parse_text_for_expenses', return_value=[]), patch(
            'services.message_handler.classify_text_message_intent', AsyncMock(return_value='webapp')
        ), patch.dict(os.environ, {'DASHBOARD_LIFF_URL': 'https://liff.line.me/abc123'}):
            reply = await process_text_message('where can I see my spending?', gemini, self._english_context())
        self.assertIn('https://liff.line.me/abc123', reply.text)

    async def test_process_text_gemini_fallback(self):
        gemini = MagicMock(spec=GeminiClient)
        with self._patch_categorize(), patch('services.message_handler.classify_text_message_intent', AsyncMock(return_value='expense')), patch(
            'services.message_handler.parse_text_for_expenses', return_value=[]
        ), patch(
            'services.message_handler.assist_parse_text',
            AsyncMock(return_value=[{'description': 'Cafe lunch', 'amount': 1200.0, 'currency': 'JPY'}]),
        ) as assist_mock, patch('services.message_handler.insert_expenses'):
            reply = await process_text_message('Lunch at cafe', gemini, self._english_context())
        assist_mock.assert_awaited_once()
        gemini.generate_reply.assert_not_called()
        self.assertIn('✅', reply.text)

    async def test_process_text_expense_intent_unparseable_returns_parse_error(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.classify_text_message_intent', AsyncMock(return_value='expense')), patch(
            'services.message_handler.parse_text_for_expenses', return_value=[]
        ), patch('services.message_handler.assist_parse_text', AsyncMock(return_value=[])):
            reply = await process_text_message('maybe an expense?', gemini, self._english_context())
        self.assertIn(receipt_parse_error_reply('en'), reply.text)
        self.assertIn('🐰', reply.text)
        gemini.generate_reply.assert_not_called()

    async def test_process_text_error(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.parse_text_for_expenses', return_value=[]), patch(
            'services.message_handler.classify_text_message_intent',
            AsyncMock(side_effect=RuntimeError('fail')),
        ):
            reply = await process_text_message('maybe an expense?', gemini, self._english_context())
        self.assertIn(error_reply_text('en'), reply.text)
        self.assertIn('🐰', reply.text)

    async def test_process_image_receipt(self):
        gemini = MagicMock(spec=GeminiClient)
        llm_result = self._valid_llm_parse(
            [{'description': 'Coffee', 'amount': 450.0, 'currency': 'JPY'}],
            450.0,
        )
        with self._patch_categorize(), patch(
            'services.message_handler.preprocess_receipt_image',
            return_value=(b'processed-jpeg', 'image/jpeg'),
        ) as preprocess_mock, patch(
            'services.message_handler.assist_parse_image',
            AsyncMock(return_value=llm_result),
        ) as parse_mock, patch('services.message_handler.insert_expenses'):
            reply = await process_image_message(b'fake-image', gemini, context=self._english_context())
        preprocess_mock.assert_called_once_with(b'fake-image')
        parse_mock.assert_awaited_once_with(b'processed-jpeg', gemini, 'image/jpeg')
        self.assertIn('✅', reply.text)

    async def test_process_image_propagates_store_name_to_items(self):
        gemini = MagicMock(spec=GeminiClient)
        llm_result = self._valid_llm_parse(
            [
                {'description': '牛乳', 'amount': 198.0, 'currency': 'JPY'},
                {'description': '食パン', 'amount': 128.0, 'currency': 'JPY'},
            ],
            326.0,
            store_name='イオン',
        )
        captured_items = []

        async def capture_enrich(items, _gemini, context=None, **kwargs):
            captured_items.extend(items)
            return items, None

        with patch(
            'services.message_handler.preprocess_receipt_image',
            return_value=(b'processed-jpeg', 'image/jpeg'),
        ), patch(
            'services.message_handler.assist_parse_image',
            AsyncMock(return_value=llm_result),
        ), patch(
            'services.message_handler._enrich_and_persist_items',
            side_effect=capture_enrich,
        ):
            reply = await process_image_message(b'fake-image', gemini, context=self._english_context())

        self.assertIn('✅', reply.text)
        self.assertEqual(len(captured_items), 2)
        self.assertEqual(captured_items[0].get('store_name'), 'イオン')
        self.assertEqual(captured_items[1].get('store_name'), 'イオン')

    async def test_process_image_non_receipt_returns_parse_error(self):
        gemini = MagicMock(spec=GeminiClient)
        parse_mock = AsyncMock(return_value=None)
        with patch(
            'services.message_handler.preprocess_receipt_image',
            return_value=(b'processed-jpeg', 'image/jpeg'),
        ), patch(
            'services.message_handler.assist_parse_image',
            parse_mock,
        ):
            reply = await process_image_message(b'cat-photo', gemini, context=self._english_context())
        self.assertIn(receipt_parse_error_reply('en'), reply.text)
        self.assertIn('🐰', reply.text)
        self.assertEqual(parse_mock.await_count, 2)
        self.assertEqual(parse_mock.await_args_list[1].kwargs.get('retry'), True)

    async def test_process_image_parse_error_when_validation_fails(self):
        gemini = MagicMock(spec=GeminiClient)
        llm_result = self._valid_llm_parse(
            [{'description': 'Item', 'amount': 10.0, 'currency': 'JPY'}],
            999.0,
        )
        parse_mock = AsyncMock(return_value=llm_result)
        with patch(
            'services.message_handler.preprocess_receipt_image',
            return_value=(b'processed-jpeg', 'image/jpeg'),
        ), patch(
            'services.message_handler.assist_parse_image',
            parse_mock,
        ):
            reply = await process_image_message(b'receipt', gemini, context=self._english_context())
        self.assertIn(receipt_parse_error_reply('en'), reply.text)
        self.assertIn('🐰', reply.text)
        self.assertEqual(parse_mock.await_count, 2)
        self.assertEqual(parse_mock.await_args_list[1].kwargs.get('retry'), True)

    async def test_process_image_retries_when_first_parse_fails_validation(self):
        gemini = MagicMock(spec=GeminiClient)
        bad = self._valid_llm_parse(
            [{'description': 'Item', 'amount': 10.0, 'currency': 'JPY'}],
            999.0,
        )
        good = self._valid_llm_parse(
            [{'description': 'Coffee', 'amount': 450.0, 'currency': 'JPY'}],
            450.0,
            store_name='カフェ',
        )
        parse_mock = AsyncMock(side_effect=[bad, good])
        with self._patch_categorize(), patch(
            'services.message_handler.preprocess_receipt_image',
            return_value=(b'processed-jpeg', 'image/jpeg'),
        ), patch(
            'services.message_handler.assist_parse_image',
            parse_mock,
        ), patch('services.message_handler.insert_expenses'):
            reply = await process_image_message(b'receipt', gemini, context=self._english_context())
        self.assertIn('✅', reply.text)
        self.assertEqual(parse_mock.await_count, 2)
        self.assertEqual(parse_mock.await_args_list[1].kwargs.get('retry'), True)

    async def test_process_image_parse_error_when_llm_returns_none(self):
        gemini = MagicMock(spec=GeminiClient)
        parse_mock = AsyncMock(return_value=None)
        with patch(
            'services.message_handler.preprocess_receipt_image',
            return_value=(b'processed-jpeg', 'image/jpeg'),
        ), patch(
            'services.message_handler.assist_parse_image',
            parse_mock,
        ):
            reply = await process_image_message(b'receipt', gemini, context=self._english_context())
        self.assertIn(receipt_parse_error_reply('en'), reply.text)
        self.assertIn('🐰', reply.text)
        self.assertEqual(parse_mock.await_count, 2)

    async def test_process_image_retries_when_first_parse_returns_none(self):
        gemini = MagicMock(spec=GeminiClient)
        good = self._valid_llm_parse(
            [{'description': 'Coffee', 'amount': 450.0, 'currency': 'JPY'}],
            450.0,
        )
        parse_mock = AsyncMock(side_effect=[None, good])
        with self._patch_categorize(), patch(
            'services.message_handler.preprocess_receipt_image',
            return_value=(b'processed-jpeg', 'image/jpeg'),
        ), patch(
            'services.message_handler.assist_parse_image',
            parse_mock,
        ), patch('services.message_handler.insert_expenses'):
            reply = await process_image_message(b'receipt', gemini, context=self._english_context())
        self.assertIn('✅', reply.text)
        self.assertEqual(parse_mock.await_count, 2)
        self.assertEqual(parse_mock.await_args_list[1].kwargs.get('retry'), True)

    async def test_process_image_usage_limit_returns_dedicated_message(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch(
            'services.message_handler.assist_parse_image',
            AsyncMock(side_effect=GeminiUsageLimitError('quota')),
        ):
            reply = await process_image_message(b'receipt', gemini, context=self._english_context())
        self.assertIn(usage_limit_reply('en'), reply.text)
        self.assertIn('🐰', reply.text)

    async def test_process_image_error(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch(
            'services.message_handler.assist_parse_image',
            AsyncMock(side_effect=RuntimeError('fail')),
        ):
            reply = await process_image_message(b'bad', gemini, context=self._english_context())
        self.assertIn(error_reply_text('en'), reply.text)
        self.assertIn('🐰', reply.text)


if __name__ == '__main__':
    unittest.main()
