import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from services.categorize import CategoryResult, classify_expense_with_memory
from services.category_memory import ItemMemoryRow, MemoryRow
from services.gemini_client import GeminiClient
from services.tenant_context import TenantContext


class TestCategorizeItemMemory(unittest.IsolatedAsyncioTestCase):
    async def test_item_mode_ignores_merchant_hard_skip(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')
        merchant_mem = MemoryRow(
            merchant_key='shimachu',
            category_code='living.plants',
            weight=Decimal('1.0'),
        )

        with patch(
            'services.merchant_resolve.resolve_raw_merchant',
            AsyncMock(return_value=('島忠ホームズ', 'shimachu')),
        ), patch(
            'services.item_normalize.normalize_item_key',
            return_value='シャワートイレ用パルプ',
        ), patch(
            'services.category_memory.lookup_item_memory',
            return_value=None,
        ), patch(
            'services.category_memory.lookup_memory',
            return_value=merchant_mem,
        ), patch(
            'services.category_memory.find_prior_expense_for_store_item',
            return_value=None,
        ), patch(
            'services.categorize.classify_expense',
            AsyncMock(return_value=CategoryResult(guessed='living.daily', alternatives=())),
        ) as classify_mock, patch(
            'services.category_memory.upsert_item_llm_seed'
        ) as seed_mock, patch(
            'services.category_memory.memory_category_is_valid',
            return_value=True,
        ):
            result = await classify_expense_with_memory(
                {
                    'description': 'シャワートイレ用パルプ',
                    'store_name': '島忠ホームズ',
                    'amount': 646,
                    'currency': 'JPY',
                },
                gemini,
                tenant=tenant,
                memory_mode='item',
            )

        classify_mock.assert_awaited_once()
        kwargs = classify_mock.await_args.kwargs
        self.assertEqual(kwargs.get('category_hint'), 'living.plants')
        self.assertEqual(result.source, 'llm')
        self.assertEqual(result.guessed, 'living.daily')
        seed_mock.assert_called_once()

    async def test_item_mode_missing_item_key_still_classifies(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')

        with patch(
            'services.merchant_resolve.resolve_raw_merchant',
            AsyncMock(return_value=('島忠ホームズ', 'shimachu')),
        ), patch(
            'services.item_normalize.normalize_item_key',
            return_value=None,
        ), patch(
            'services.category_memory.lookup_memory',
            return_value=None,
        ), patch(
            'services.categorize.classify_expense',
            AsyncMock(return_value=CategoryResult(guessed='unknown', alternatives=())),
        ) as classify_mock, patch(
            'services.category_memory.upsert_item_llm_seed'
        ) as seed_mock:
            result = await classify_expense_with_memory(
                {'description': '商品', 'store_name': '島忠', 'amount': 100, 'currency': 'JPY'},
                gemini,
                tenant=tenant,
                memory_mode='item',
            )

        classify_mock.assert_awaited_once()
        seed_mock.assert_not_called()
        self.assertEqual(result.source, 'llm')
        self.assertIsNone(result.item_key)

    async def test_store_item_high_weight_skips_llm(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')
        hit = ItemMemoryRow(
            memory_kind='store_item',
            item_key='シャワートイレ用パルプ',
            category_code='living.daily',
            weight=Decimal('1.0'),
            merchant_key='shimachu',
        )

        with patch(
            'services.merchant_resolve.resolve_raw_merchant',
            AsyncMock(return_value=('島忠ホームズ', 'shimachu')),
        ), patch(
            'services.item_normalize.normalize_item_key',
            return_value='シャワートイレ用パルプ',
        ), patch(
            'services.category_memory.lookup_item_memory',
            return_value=hit,
        ), patch(
            'services.category_memory.memory_category_is_valid',
            return_value=True,
        ), patch(
            'services.categorize.classify_expense',
            AsyncMock(),
        ) as classify_mock:
            result = await classify_expense_with_memory(
                {
                    'description': 'シャワートイレ用パルプ',
                    'store_name': '島忠ホームズ',
                    'amount': 646,
                    'currency': 'JPY',
                },
                gemini,
                tenant=tenant,
                memory_mode='item',
            )

        classify_mock.assert_not_awaited()
        self.assertEqual(result.source, 'item_memory')
        self.assertEqual(result.guessed, 'living.daily')
        self.assertEqual(result.item_memory_kind, 'store_item')

    async def test_item_only_used_when_no_store_item(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')
        item_only = ItemMemoryRow(
            memory_kind='item_only',
            item_key='シャワートイレ用パルプ',
            category_code='living.daily',
            weight=Decimal('1.0'),
            merchant_key=None,
        )

        def _lookup(tenant_arg, *, memory_kind, item_key, merchant_key=None):
            if memory_kind == 'store_item':
                return None
            return item_only

        with patch(
            'services.merchant_resolve.resolve_raw_merchant',
            AsyncMock(return_value=('マツキヨ', 'matsukiyo')),
        ), patch(
            'services.item_normalize.normalize_item_key',
            return_value='シャワートイレ用パルプ',
        ), patch(
            'services.category_memory.lookup_item_memory',
            side_effect=_lookup,
        ), patch(
            'services.category_memory.memory_category_is_valid',
            return_value=True,
        ), patch(
            'services.categorize.classify_expense',
            AsyncMock(),
        ) as classify_mock:
            result = await classify_expense_with_memory(
                {
                    'description': 'シャワートイレ用パルプ',
                    'store_name': 'マツキヨ',
                    'amount': 300,
                    'currency': 'JPY',
                },
                gemini,
                tenant=tenant,
                memory_mode='item',
            )

        classify_mock.assert_not_awaited()
        self.assertEqual(result.source, 'item_memory')
        self.assertEqual(result.item_memory_kind, 'item_only')

    async def test_store_item_preferred_over_item_only(self):
        gemini = MagicMock(spec=GeminiClient)
        tenant = TenantContext.personal('u1')
        store_hit = ItemMemoryRow(
            memory_kind='store_item',
            item_key='牛乳',
            category_code='food.grocery',
            weight=Decimal('1.0'),
            merchant_key='aeon',
        )

        with patch(
            'services.merchant_resolve.resolve_raw_merchant',
            AsyncMock(return_value=('イオン', 'aeon')),
        ), patch(
            'services.item_normalize.normalize_item_key',
            return_value='牛乳',
        ), patch(
            'services.category_memory.lookup_item_memory',
            return_value=store_hit,
        ) as lookup_mock, patch(
            'services.category_memory.memory_category_is_valid',
            return_value=True,
        ), patch(
            'services.categorize.classify_expense',
            AsyncMock(),
        ) as classify_mock:
            result = await classify_expense_with_memory(
                {'description': '牛乳', 'store_name': 'イオン', 'amount': 198, 'currency': 'JPY'},
                gemini,
                tenant=tenant,
                memory_mode='item',
            )

        classify_mock.assert_not_awaited()
        self.assertEqual(result.item_memory_kind, 'store_item')
        self.assertEqual(result.guessed, 'food.grocery')
        # first lookup should be store_item
        self.assertEqual(lookup_mock.call_args_list[0].kwargs['memory_kind'], 'store_item')


if __name__ == '__main__':
    unittest.main()
