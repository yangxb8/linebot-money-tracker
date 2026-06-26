import unittest
from unittest.mock import AsyncMock, MagicMock

from services.gemini_client import GeminiClient
from services.merchant_extract import extract_merchant_name, validate_merchant_extract_response


class TestMerchantExtract(unittest.IsolatedAsyncioTestCase):
    def test_validate_merchant_found(self):
        self.assertEqual(
            validate_merchant_extract_response({'merchant_name': 'スターバックス'}),
            'スターバックス',
        )

    def test_validate_null_generic(self):
        self.assertIsNone(validate_merchant_extract_response({'merchant_name': None}))
        self.assertIsNone(validate_merchant_extract_response({'merchant_name': '食費'}))

    def test_validate_invalid_schema(self):
        self.assertIsNone(validate_merchant_extract_response({'bad': 'x'}))

    async def test_extract_merchant_name_success(self):
        gemini = MagicMock(spec=GeminiClient)
        gemini.generate_reply = AsyncMock(return_value='{"merchant_name": "ローソン"}')
        result = await extract_merchant_name('ローソン おにぎり', gemini, amount=150, currency='JPY')
        self.assertEqual(result, 'ローソン')

    async def test_extract_merchant_name_invalid_json(self):
        gemini = MagicMock(spec=GeminiClient)
        gemini.generate_reply = AsyncMock(return_value='not json')
        result = await extract_merchant_name('ローソン', gemini)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
