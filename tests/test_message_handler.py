import os
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from services.ai_assist import ReceiptImageParseResult
from services.categorize import CategoryResult
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
        self.assertIn('Detected expense(s):', text)
        self.assertIn('1️⃣ Lunch:', text)
        self.assertIn('120.0', text)


class TestMessageHandlerAsync(unittest.IsolatedAsyncioTestCase):
    def _english_context(self):
        return MessageContext(
            tenant=TenantContext.personal('u1'),
            source_message_id='m1',
            reply_language='en',
        )

    def _patch_categorize(self):
        return patch(
            'services.message_handler.classify_expense',
            AsyncMock(return_value=CategoryResult(guessed='unknown', alternatives=())),
        )

    def _valid_llm_parse(self, items, total):
        return ReceiptImageParseResult(items=items, total=Decimal(str(total)), currency='JPY')

    async def test_process_text_expense_with_parser(self):
        gemini = MagicMock(spec=GeminiClient)
        with self._patch_categorize(), patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=True)), patch(
            'services.message_handler.parse_text_for_expenses',
            return_value=[{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}],
        ), patch('services.message_handler.insert_expenses'):
            reply = await process_text_message('Lunch 120 THB', gemini, self._english_context())
        self.assertIn('Detected expense(s):', reply.text)
        gemini.generate_reply.assert_not_called()

    async def test_process_text_non_expense(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=False)):
            reply = await process_text_message('Hello bot', gemini, self._english_context())
        self.assertEqual(reply.text, canned_unsupported_reply('en'))

    async def test_process_text_gemini_fallback(self):
        gemini = MagicMock(spec=GeminiClient)
        with self._patch_categorize(), patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=True)), patch(
            'services.message_handler.parse_text_for_expenses', return_value=[]
        ), patch(
            'services.message_handler.assist_parse_text',
            AsyncMock(return_value=[{'description': 'Cafe lunch', 'amount': 1200.0, 'currency': 'JPY'}]),
        ) as assist_mock, patch('services.message_handler.insert_expenses'):
            reply = await process_text_message('Lunch at cafe', gemini, self._english_context())
        assist_mock.assert_awaited_once()
        gemini.generate_reply.assert_not_called()
        self.assertIn('Detected expense(s):', reply.text)

    async def test_process_text_expense_intent_unparseable_returns_parse_error(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=True)), patch(
            'services.message_handler.parse_text_for_expenses', return_value=[]
        ), patch('services.message_handler.assist_parse_text', AsyncMock(return_value=[])):
            reply = await process_text_message('maybe an expense?', gemini, self._english_context())
        self.assertEqual(reply.text, receipt_parse_error_reply('en'))
        gemini.generate_reply.assert_not_called()

    async def test_process_text_error(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(side_effect=RuntimeError('fail'))):
            reply = await process_text_message('Lunch 120', gemini, self._english_context())
        self.assertEqual(reply.text, error_reply_text('en'))

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
        self.assertIn('Detected expense(s):', reply.text)

    async def test_process_image_non_receipt_returns_parse_error(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.assist_parse_image', AsyncMock(return_value=None)):
            reply = await process_image_message(b'cat-photo', gemini, context=self._english_context())
        self.assertEqual(reply.text, receipt_parse_error_reply('en'))

    async def test_process_image_parse_error_when_validation_fails(self):
        gemini = MagicMock(spec=GeminiClient)
        llm_result = self._valid_llm_parse(
            [{'description': 'Item', 'amount': 10.0, 'currency': 'JPY'}],
            999.0,
        )
        with patch('services.message_handler.assist_parse_image', AsyncMock(return_value=llm_result)):
            reply = await process_image_message(b'receipt', gemini, context=self._english_context())
        self.assertEqual(reply.text, receipt_parse_error_reply('en'))

    async def test_process_image_parse_error_when_llm_returns_none(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.assist_parse_image', AsyncMock(return_value=None)):
            reply = await process_image_message(b'receipt', gemini, context=self._english_context())
        self.assertEqual(reply.text, receipt_parse_error_reply('en'))

    async def test_process_image_usage_limit_returns_dedicated_message(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch(
            'services.message_handler.assist_parse_image',
            AsyncMock(side_effect=GeminiUsageLimitError('quota')),
        ):
            reply = await process_image_message(b'receipt', gemini, context=self._english_context())
        self.assertEqual(reply.text, usage_limit_reply('en'))

    async def test_process_image_error(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch(
            'services.message_handler.assist_parse_image',
            AsyncMock(side_effect=RuntimeError('fail')),
        ):
            reply = await process_image_message(b'bad', gemini, context=self._english_context())
        self.assertEqual(reply.text, error_reply_text('en'))


if __name__ == '__main__':
    unittest.main()
