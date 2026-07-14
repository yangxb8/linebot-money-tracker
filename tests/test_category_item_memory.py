import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services.category_memory import (
    apply_item_silent_confirm,
    lookup_item_memory,
    record_item_user_correction,
    upsert_item_llm_seed,
)
from services.tenant_context import TenantContext


class _ExecuteResult:
    def __init__(self, data):
        self.data = data


class TestCategoryItemMemory(unittest.TestCase):
    def setUp(self):
        self.tenant = TenantContext.personal('user-a')

    @patch('services.category_memory.is_supabase_configured', return_value=True)
    @patch('services.category_memory.get_supabase_client')
    def test_upsert_llm_seed_store_item_only(self, get_client, _configured):
        client = MagicMock()
        get_client.return_value = client
        table = MagicMock()
        client.table.return_value = table
        select_query = MagicMock()
        table.select.return_value = select_query
        select_query.eq.return_value = select_query
        select_query.is_.return_value = select_query
        select_query.limit.return_value = select_query
        select_query.execute.return_value = _ExecuteResult([])
        table.insert.return_value = MagicMock(execute=MagicMock())

        upsert_item_llm_seed(
            self.tenant,
            merchant_key='shimachu',
            item_key='陶器プランター',
            category_code='living.plants',
        )
        table.insert.assert_called_once()
        payload = table.insert.call_args.args[0]
        self.assertEqual(payload['memory_kind'], 'store_item')
        self.assertEqual(payload['last_source'], 'llm')
        self.assertNotEqual(payload['memory_kind'], 'item_only')

    @patch('services.category_memory.is_supabase_configured', return_value=True)
    @patch('services.category_memory.get_supabase_client')
    def test_user_correction_writes_store_item_and_item_only(self, get_client, _configured):
        client = MagicMock()
        get_client.return_value = client
        table = MagicMock()
        client.table.return_value = table
        select_query = MagicMock()
        table.select.return_value = select_query
        select_query.eq.return_value = select_query
        select_query.is_.return_value = select_query
        select_query.limit.return_value = select_query
        select_query.execute.return_value = _ExecuteResult([])
        table.insert.return_value = MagicMock(execute=MagicMock())

        record_item_user_correction(
            self.tenant,
            item_key='シャワートイレ用パルプ',
            category_code='living.daily',
            merchant_key='shimachu',
            corrected_by='user-a',
        )
        self.assertEqual(table.insert.call_count, 2)
        kinds = {call.args[0]['memory_kind'] for call in table.insert.call_args_list}
        self.assertEqual(kinds, {'store_item', 'item_only'})
        for call in table.insert.call_args_list:
            self.assertEqual(call.args[0]['weight'], 1.0)
            self.assertEqual(call.args[0]['last_source'], 'user_correction')

    @patch('services.category_memory.is_supabase_configured', return_value=True)
    @patch('services.category_memory.get_supabase_client')
    def test_silent_confirm_store_item_only(self, get_client, _configured):
        client = MagicMock()
        get_client.return_value = client
        table = MagicMock()
        client.table.return_value = table
        select_query = MagicMock()
        table.select.return_value = select_query
        select_query.eq.return_value = select_query
        select_query.limit.return_value = select_query
        select_query.execute.return_value = _ExecuteResult(
            [{'id': 'r1', 'weight': 0.25, 'hit_count': 1}]
        )
        update_query = MagicMock()
        table.update.return_value = update_query
        update_query.eq.return_value = update_query

        apply_item_silent_confirm(
            self.tenant,
            merchant_key='shimachu',
            item_key='陶器プランター',
            category_code='living.plants',
        )
        payload = table.update.call_args.args[0]
        self.assertEqual(payload['memory_kind'], 'store_item')
        self.assertEqual(payload['last_source'], 'silent_confirm')
        self.assertAlmostEqual(payload['weight'], 0.75)

    @patch('services.category_memory.is_supabase_configured', return_value=True)
    @patch('services.category_memory.get_supabase_client')
    def test_lookup_item_memory(self, get_client, _configured):
        client = MagicMock()
        get_client.return_value = client
        table = MagicMock()
        client.table.return_value = table
        query = MagicMock()
        table.select.return_value = query
        query.eq.return_value = query
        query.limit.return_value = query
        query.execute.return_value = _ExecuteResult(
            [
                {
                    'memory_kind': 'store_item',
                    'merchant_key': 'shimachu',
                    'item_key': '牛乳',
                    'category_code': 'food.grocery',
                    'weight': 1.0,
                    'display_merchant': '島忠',
                }
            ]
        )
        row = lookup_item_memory(
            self.tenant,
            memory_kind='store_item',
            merchant_key='shimachu',
            item_key='牛乳',
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.category_code, 'food.grocery')
        self.assertEqual(row.weight, Decimal('1.0'))


if __name__ == '__main__':
    unittest.main()
