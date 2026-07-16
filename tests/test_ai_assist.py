import unittest
from decimal import Decimal
from unittest.mock import AsyncMock

from services.ai_assist import (
    ReceiptImageParseResult,
    _RECEIPT_IMAGE_PROMPT,
    _RECEIPT_IMAGE_RETRY_PROMPT,
    assist_parse_image,
    assist_parse_ocr,
    assist_parse_text,
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

    def test_validate_receipt_image_parse_accepts_store_name(self):
        result = validate_receipt_image_parse(
            {
                'store_name': 'イオン',
                'items': [{'description': '牛乳', 'amount': 198, 'currency': 'JPY'}],
                'total': 198,
                'currency': 'JPY',
            }
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.store_name, 'イオン')

    def test_validate_receipt_image_parse_accepts_null_store_name(self):
        result = validate_receipt_image_parse(
            {
                'store_name': None,
                'items': [{'description': 'Coffee', 'amount': 450, 'currency': 'JPY'}],
                'total': 450,
                'currency': 'JPY',
            }
        )
        self.assertIsNotNone(result)
        self.assertIsNone(result.store_name)

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

    async def test_assist_parse_text_validates_response(self):
        gemini = AsyncMock()
        gemini.generate_json_reply = AsyncMock(
            return_value='[{"description":"便利店","amount":861,"currency":"JPY"}]'
        )

        items = await assist_parse_text('861便利店', gemini)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['amount'], 861)
        self.assertEqual(items[0]['currency'], 'JPY')

    async def test_assist_parse_text_returns_empty_array_for_non_expense(self):
        gemini = AsyncMock()
        gemini.generate_json_reply = AsyncMock(return_value='[]')

        items = await assist_parse_text('什么是861便利店？', gemini)
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
        self.assertEqual(
            gemini.generate_json_reply_with_image.await_args.args[0],
            _RECEIPT_IMAGE_PROMPT,
        )

    async def test_assist_parse_image_retry_uses_retry_prompt(self):
        gemini = AsyncMock()
        gemini.generate_json_reply_with_image = AsyncMock(
            return_value=(
                '{"items":[{"description":"Coffee","amount":450,"currency":"JPY"}],'
                '"total":450,"currency":"JPY"}'
            )
        )

        result = await assist_parse_image(b'fake-image', gemini, 'image/jpeg', retry=True)
        self.assertIsInstance(result, ReceiptImageParseResult)
        self.assertEqual(
            gemini.generate_json_reply_with_image.await_args.args[0],
            _RECEIPT_IMAGE_RETRY_PROMPT,
        )


if __name__ == '__main__':
    unittest.main()
