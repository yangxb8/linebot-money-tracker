import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.gemini_client import GeminiClient
from services.merchant_resolve import merchant_key_from_expense_row, resolve_raw_merchant


class TestMerchantKeyFromExpenseRow(unittest.TestCase):
    def test_prefers_metadata_store_name(self):
        row = {
            'description': '牛乳',
            'metadata': {'store_name': 'イオン'},
        }
        self.assertEqual(merchant_key_from_expense_row(row), 'aeon')

    def test_falls_back_to_description_heuristic(self):
        row = {
            'description': 'スターバックス ラテ',
            'metadata': {},
        }
        key = merchant_key_from_expense_row(row)
        self.assertIsNotNone(key)


class TestResolveRawMerchant(unittest.IsolatedAsyncioTestCase):
    async def test_store_name_skips_merchant_extract(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch(
            'services.merchant_extract.extract_merchant_name',
            AsyncMock(),
        ) as extract_mock, patch(
            'services.merchant_normalize.normalize_merchant_key',
            return_value='aeon',
        ):
            raw, key = await resolve_raw_merchant(
                {'description': '牛乳', 'store_name': 'イオン', 'amount': 198, 'currency': 'JPY'},
                gemini,
            )
        extract_mock.assert_not_awaited()
        self.assertEqual(raw, 'イオン')
        self.assertEqual(key, 'aeon')

    async def test_falls_back_to_description_when_store_normalize_fails(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch(
            'services.merchant_normalize.normalize_merchant_key',
            side_effect=[None, 'unknown_shop'],
        ), patch(
            'services.merchant_extract.extract_merchant_name',
            AsyncMock(return_value='Unknown Shop'),
        ) as extract_mock:
            raw, key = await resolve_raw_merchant(
                {'description': '牛乳', 'store_name': '???', 'amount': 198, 'currency': 'JPY'},
                gemini,
            )
        extract_mock.assert_awaited_once()
        self.assertEqual(raw, 'Unknown Shop')
        self.assertEqual(key, 'unknown_shop')


if __name__ == '__main__':
    unittest.main()
