import unittest
from unittest.mock import AsyncMock

from services.ai_assist import assist_parse_image, assist_parse_ocr, validate_expense_items


class TestAiAssist(unittest.TestCase):
    def test_validate_expense_items_accepts_valid_payload(self):
        items = validate_expense_items(
            [{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['description'], 'Lunch')

    def test_validate_expense_items_rejects_missing_fields(self):
        items = validate_expense_items([{'description': 'Lunch', 'amount': 120.0}])
        self.assertEqual(items, [])

    def test_validate_expense_items_rejects_non_array(self):
        items = validate_expense_items({'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'})
        self.assertEqual(items, [])


class TestAiAssistAsync(unittest.IsolatedAsyncioTestCase):
    async def test_assist_parse_ocr_validates_response(self):
        gemini = AsyncMock()
        gemini.generate_json_reply = AsyncMock(
            return_value='[{"description":"Coffee","amount":4.5,"currency":"USD"}]'
        )

        items = await assist_parse_ocr('Coffee 4.50 USD', gemini)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['currency'], 'USD')

    async def test_assist_parse_ocr_rejects_invalid_schema(self):
        gemini = AsyncMock()
        gemini.generate_json_reply = AsyncMock(
            return_value='[{"description":"Coffee","amount":"four"}]'
        )

        items = await assist_parse_ocr('Coffee four dollars', gemini)
        self.assertEqual(items, [])

    async def test_assist_parse_image_validates_response(self):
        gemini = AsyncMock()
        gemini.generate_json_reply_with_image = AsyncMock(
            return_value='[{"description":"Coffee","amount":450,"currency":"JPY"}]'
        )

        items = await assist_parse_image(b'fake-image', gemini, 'image/jpeg')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['currency'], 'JPY')
        gemini.generate_json_reply_with_image.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
