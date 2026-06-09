import unittest
from decimal import Decimal
from unittest.mock import AsyncMock

from services.ai_assist import (
    ReceiptImageParseResult,
    assist_parse_image,
    assist_parse_ocr,
    validate_expense_items,
    validate_receipt_image_parse,
)


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

    def test_validate_receipt_image_parse_accepts_wrapper(self):
        result = validate_receipt_image_parse(
            {
                'items': [{'description': 'Coffee', 'amount': 450, 'currency': 'JPY'}],
                'total': 450,
                'currency': 'JPY',
            }
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.total, Decimal('450'))
        self.assertEqual(result.currency, 'JPY')

    def test_validate_receipt_image_parse_rejects_missing_total(self):
        result = validate_receipt_image_parse(
            {
                'items': [{'description': 'Coffee', 'amount': 450, 'currency': 'JPY'}],
                'currency': 'JPY',
            }
        )
        self.assertIsNone(result)


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
            return_value=(
                '{"items":[{"description":"Coffee","amount":450,"currency":"JPY"}],'
                '"total":450,"currency":"JPY"}'
            )
        )

        result = await assist_parse_image(b'fake-image', gemini, 'image/jpeg')
        self.assertIsInstance(result, ReceiptImageParseResult)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0]['currency'], 'JPY')
        self.assertEqual(result.total, Decimal('450'))
        gemini.generate_json_reply_with_image.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
