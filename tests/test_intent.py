import unittest
from unittest.mock import AsyncMock, MagicMock

from services.intent import (
    _parse_combined_intent_response,
    _parse_intent_response,
    classify_text_message_intent,
    is_expense_intent_image,
    is_expense_intent_text,
)


class TestParseIntentResponse(unittest.TestCase):
    def test_parses_json_true(self):
        self.assertTrue(_parse_intent_response('{"is_expense": true}'))

    def test_parses_json_false(self):
        self.assertFalse(_parse_intent_response('{"is_expense": false}'))

    def test_rejects_invalid_json(self):
        self.assertFalse(_parse_intent_response('not json'))


class TestParseCombinedIntentResponse(unittest.TestCase):
    def test_parses_expense(self):
        self.assertEqual(_parse_combined_intent_response('{"intent": "expense"}'), 'expense')

    def test_parses_webapp(self):
        self.assertEqual(_parse_combined_intent_response('{"intent": "webapp"}'), 'webapp')

    def test_parses_other(self):
        self.assertEqual(_parse_combined_intent_response('{"intent": "other"}'), 'other')

    def test_invalid_defaults_to_other(self):
        self.assertEqual(_parse_combined_intent_response('not json'), 'other')


class TestIntentAsync(unittest.IsolatedAsyncioTestCase):
    async def test_combined_intent_classifies_expense(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(return_value='{"intent": "expense"}')

        result = await classify_text_message_intent('Lunch 120 THB at cafe', gemini)
        self.assertEqual(result, 'expense')
        gemini.generate_reply.assert_awaited_once()

    async def test_combined_intent_classifies_webapp(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(return_value='{"intent": "webapp"}')

        result = await classify_text_message_intent('how can I see my expenses online?', gemini)
        self.assertEqual(result, 'webapp')

    async def test_combined_intent_classifies_other(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(return_value='{"intent": "other"}')

        result = await classify_text_message_intent('Hello bot', gemini)
        self.assertEqual(result, 'other')

    async def test_text_intent_calls_gemini(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(return_value='{"intent": "expense"}')

        result = await is_expense_intent_text('Lunch 120 THB at cafe', gemini)
        self.assertTrue(result)
        gemini.generate_reply.assert_awaited_once()

    async def test_text_intent_rejects_greeting(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(return_value='{"intent": "other"}')

        result = await is_expense_intent_text('Hello bot', gemini)
        self.assertFalse(result)

    async def test_text_intent_rejects_empty(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock()

        self.assertFalse(await is_expense_intent_text('', gemini))
        self.assertFalse(await is_expense_intent_text(None, gemini))
        gemini.generate_reply.assert_not_awaited()

    async def test_image_intent_accepts_receipt(self):
        gemini = MagicMock()
        gemini.generate_reply_with_image = AsyncMock(return_value='{"is_expense": true}')

        result = await is_expense_intent_image(b'fake-image', gemini)
        self.assertTrue(result)
        gemini.generate_reply_with_image.assert_awaited_once()

    async def test_image_intent_rejects_non_receipt(self):
        gemini = MagicMock()
        gemini.generate_reply_with_image = AsyncMock(return_value='{"is_expense": false}')

        result = await is_expense_intent_image(b'cat-photo', gemini)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
