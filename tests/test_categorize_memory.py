import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from services.categorize import CategoryResult, CategoryResultWithProvenance, classify_expense_with_memory
from services.category_memory import MemoryRow
from services.gemini_client import GeminiClient
from services.tenant_context import TenantContext


class TestCategorizeMemory(unittest.IsolatedAsyncioTestCase):
    async def test_memory_hit_skips_classify_expense(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')
        memory = MemoryRow(
            merchant_key='starbucks',
            category_code='food.dining',
            weight=Decimal('1.0'),
        )

        with patch(
            'services.merchant_extract.extract_merchant_name',
            AsyncMock(return_value='スターバックス'),
        ), patch('services.merchant_normalize.normalize_merchant_key', return_value='starbucks'), patch(
            'services.category_memory.find_prior_expense_for_merchant',
            return_value=None,
        ), patch('services.category_memory.lookup_memory', return_value=memory), patch(
            'services.category_memory.memory_category_is_valid',
            return_value=True,
        ), patch('services.categorize.classify_expense', AsyncMock()) as classify_mock:
            result = await classify_expense_with_memory(
                {'description': 'スターバックス ラテ', 'amount': 580, 'currency': 'JPY'},
                gemini,
                tenant=tenant,
            )

        classify_mock.assert_not_awaited()
        self.assertEqual(result.source, 'memory')
        self.assertEqual(result.guessed, 'food.dining')
        self.assertEqual(result.alternatives, ())

    async def test_generic_merchant_always_llm(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')

        with patch(
            'services.merchant_extract.extract_merchant_name',
            AsyncMock(return_value=None),
        ), patch('services.merchant_normalize.normalize_merchant_key', return_value=None), patch(
            'services.categorize.classify_expense',
            AsyncMock(return_value=CategoryResult(guessed='unknown', alternatives=())),
        ) as classify_mock, patch('services.category_memory.upsert_llm_seed') as seed_mock:
            result = await classify_expense_with_memory(
                {'description': '食費 5000円', 'amount': 5000, 'currency': 'JPY'},
                gemini,
                tenant=tenant,
            )

        classify_mock.assert_awaited_once()
        seed_mock.assert_not_called()
        self.assertEqual(result.source, 'llm')

    async def test_llm_path_seeds_memory(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')

        with patch(
            'services.merchant_extract.extract_merchant_name',
            AsyncMock(return_value='ローソン'),
        ), patch('services.merchant_normalize.normalize_merchant_key', return_value='lawson'), patch(
            'services.category_memory.find_prior_expense_for_merchant',
            return_value=None,
        ), patch('services.category_memory.lookup_memory', return_value=None), patch(
            'services.categorize.classify_expense',
            AsyncMock(return_value=CategoryResult(guessed='food.grocery', alternatives=())),
        ), patch('services.category_memory.upsert_llm_seed') as seed_mock:
            result = await classify_expense_with_memory(
                {'description': 'ローソン おにぎり', 'amount': 150, 'currency': 'JPY'},
                gemini,
                tenant=tenant,
            )

        seed_mock.assert_called_once()
        self.assertEqual(result.source, 'llm')
        self.assertIsInstance(result, CategoryResultWithProvenance)


if __name__ == '__main__':
    unittest.main()
