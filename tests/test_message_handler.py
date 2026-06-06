import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.categorize import CategoryResult
from services.gemini_client import GeminiClient
from services.message_handler import (
    CANNED_UNSUPPORTED_REPLY,
    ERROR_REPLY_TEXT,
    format_expense_items,
    process_image_message,
    process_text_message,
)


class TestFormatExpenseItems(unittest.TestCase):
    def test_formats_single_item(self):
        text = format_expense_items([{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}])
        self.assertIn('Detected expense(s):', text)
        self.assertIn('120.0', text)


class TestMessageHandlerAsync(unittest.IsolatedAsyncioTestCase):
    def _patch_categorize(self):
        return patch(
            'services.message_handler.classify_expense',
            AsyncMock(return_value=CategoryResult(guessed='unknown', alternatives=())),
        )

    async def test_process_text_expense_with_parser(self):
        gemini = MagicMock(spec=GeminiClient)
        with self._patch_categorize(), patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=True)), patch(
            'services.message_handler.parse_text_for_expenses',
            return_value=[{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}],
        ), patch('services.message_handler.insert_expenses'):
            reply = await process_text_message('Lunch 120 THB', gemini)
        self.assertIn('Detected expense(s):', reply.text)
        gemini.generate_reply.assert_not_called()

    async def test_process_text_non_expense(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=False)):
            reply = await process_text_message('Hello bot', gemini)
        self.assertEqual(reply.text, CANNED_UNSUPPORTED_REPLY)

    async def test_process_text_gemini_fallback(self):
        gemini = MagicMock(spec=GeminiClient)
        gemini.generate_reply = AsyncMock(return_value='Gemini parsed reply')
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(return_value=True)), patch(
            'services.message_handler.parse_text_for_expenses', return_value=[]
        ):
            reply = await process_text_message('Lunch at cafe', gemini)
        self.assertEqual(reply.text, 'Gemini parsed reply')

    async def test_process_text_error(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.is_expense_intent_text', AsyncMock(side_effect=RuntimeError('fail'))):
            reply = await process_text_message('Lunch 120', gemini)
        self.assertEqual(reply.text, ERROR_REPLY_TEXT)

    async def test_process_image_receipt(self):
        gemini = MagicMock(spec=GeminiClient)
        with self._patch_categorize(), patch('services.message_handler.is_expense_intent_image', AsyncMock(return_value=True)), patch(
            'services.message_handler.extract_text_from_image_bytes', return_value=['Coffee 450 JPY']
        ), patch(
            'services.message_handler.parse_text_for_expenses',
            return_value=[{'description': 'Coffee', 'amount': 450.0, 'currency': 'JPY'}],
        ), patch('services.message_handler.insert_expenses'):
            reply = await process_image_message(b'fake-image', gemini)
        self.assertIn('Detected expense(s):', reply.text)

    async def test_process_image_non_receipt(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.is_expense_intent_image', AsyncMock(return_value=False)), patch(
            'services.message_handler.extract_text_from_image_bytes'
        ) as ocr_mock:
            reply = await process_image_message(b'cat-photo', gemini)
        ocr_mock.assert_not_called()
        self.assertEqual(reply.text, CANNED_UNSUPPORTED_REPLY)

    async def test_process_image_ocr_ai_assist_fallback(self):
        gemini = MagicMock(spec=GeminiClient)
        with self._patch_categorize(), patch('services.message_handler.is_expense_intent_image', AsyncMock(return_value=True)), patch(
            'services.message_handler.extract_text_from_image_bytes', return_value=['receipt noise']
        ), patch('services.message_handler.parse_text_for_expenses', return_value=[]), patch(
            'services.message_handler.assist_parse_ocr',
            AsyncMock(return_value=[{'description': 'Item', 'amount': 10.0, 'currency': 'USD'}]),
        ), patch('services.message_handler.assist_parse_image', AsyncMock(return_value=[])) as image_mock, patch(
            'services.message_handler.insert_expenses',
        ):
            reply = await process_image_message(b'receipt', gemini)
        image_mock.assert_not_awaited()
        self.assertIn('Detected expense(s):', reply.text)

    async def test_process_image_llm_fallback_when_ocr_fails(self):
        gemini = MagicMock(spec=GeminiClient)
        with self._patch_categorize(), patch('services.message_handler.is_expense_intent_image', AsyncMock(return_value=True)), patch(
            'services.message_handler.extract_text_from_image_bytes', return_value=[]
        ), patch('services.message_handler.assist_parse_image', AsyncMock(
            return_value=[{'description': 'Coffee', 'amount': 450.0, 'currency': 'JPY'}]
        )) as image_mock, patch('services.message_handler.insert_expenses'):
            reply = await process_image_message(b'receipt', gemini)
        image_mock.assert_awaited_once()
        self.assertIn('Detected expense(s):', reply.text)
        self.assertIn('Coffee', reply.text)

    async def test_process_image_error(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch('services.message_handler.is_expense_intent_image', AsyncMock(side_effect=RuntimeError('fail'))):
            reply = await process_image_message(b'bad', gemini)
        self.assertEqual(reply.text, ERROR_REPLY_TEXT)


if __name__ == '__main__':
    unittest.main()
