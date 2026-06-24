import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services.category_memory import (
    MEMORY_SKIP_WEIGHT_THRESHOLD,
    apply_silent_confirm,
    lookup_memory,
    record_user_correction,
    upsert_llm_seed,
)
from services.tenant_context import TenantContext


class _ExecuteResult:
    def __init__(self, data):
        self.data = data


class TestCategoryMemory(unittest.TestCase):
    def setUp(self):
        self.tenant = TenantContext.personal('user-a')
        self.group = TenantContext.group('group-1', 'user-a')

    @patch('services.category_memory.is_supabase_configured', return_value=True)
    @patch('services.category_memory.get_supabase_client')
    def test_lookup_memory(self, get_client, _configured):
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
                    'merchant_key': 'starbucks',
                    'category_code': 'food.dining',
                    'weight': 1.0,
                    'display_merchant': 'スターバックス',
                }
            ]
        )

        row = lookup_memory(self.tenant, 'starbucks')
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.category_code, 'food.dining')
        self.assertGreaterEqual(row.weight, MEMORY_SKIP_WEIGHT_THRESHOLD)

    @patch('services.category_memory.is_supabase_configured', return_value=True)
    @patch('services.category_memory.get_supabase_client')
    def test_upsert_llm_seed_increments_weight(self, get_client, _configured):
        client = MagicMock()
        get_client.return_value = client
        table = MagicMock()
        client.table.return_value = table
        select_query = MagicMock()
        table.select.return_value = select_query
        select_query.eq.return_value = select_query
        select_query.limit.return_value = select_query
        select_query.execute.return_value = _ExecuteResult([{'id': 'm1', 'weight': 0.25, 'hit_count': 1}])
        update_query = MagicMock()
        table.update.return_value = update_query
        update_query.eq.return_value = update_query

        upsert_llm_seed(
            self.tenant,
            merchant_key='lawson',
            category_code='food.grocery',
            display_merchant='ローソン',
        )
        update_query.execute.assert_called_once()
        payload = table.update.call_args.args[0]
        self.assertEqual(payload['last_source'], 'llm')
        self.assertAlmostEqual(payload['weight'], 0.5)

    @patch('services.category_memory.is_supabase_configured', return_value=True)
    @patch('services.category_memory.get_supabase_client')
    def test_record_user_correction_sets_weight_one(self, get_client, _configured):
        client = MagicMock()
        get_client.return_value = client
        table = MagicMock()
        client.table.return_value = table
        select_query = MagicMock()
        table.select.return_value = select_query
        select_query.eq.return_value = select_query
        select_query.limit.return_value = select_query
        select_query.execute.return_value = _ExecuteResult([])
        insert_query = MagicMock()
        table.insert.return_value = insert_query

        record_user_correction(
            self.tenant,
            description='スターバックス ラテ',
            category_code='food.dining',
            merchant_key='starbucks',
        )
        payload = table.insert.call_args.args[0]
        self.assertEqual(payload['weight'], 1.0)
        self.assertEqual(payload['last_source'], 'user_correction')

    @patch('services.category_memory.is_supabase_configured', return_value=True)
    @patch('services.category_memory.get_supabase_client')
    def test_tenant_isolation_filter(self, get_client, _configured):
        client = MagicMock()
        get_client.return_value = client
        table = MagicMock()
        client.table.return_value = table
        query = MagicMock()
        table.select.return_value = query
        query.eq.return_value = query
        query.limit.return_value = query
        query.execute.return_value = _ExecuteResult([])

        lookup_memory(self.group, 'don_quijote')
        eq_calls = [call.args for call in query.eq.call_args_list]
        self.assertIn(('tenant_type', 'group'), eq_calls)
        self.assertIn(('tenant_id', 'group-1'), eq_calls)

    @patch('services.category_memory.is_supabase_configured', return_value=True)
    @patch('services.category_memory.get_supabase_client')
    def test_silent_confirm_adds_half_weight(self, get_client, _configured):
        client = MagicMock()
        get_client.return_value = client
        table = MagicMock()
        client.table.return_value = table
        select_query = MagicMock()
        table.select.return_value = select_query
        select_query.eq.return_value = select_query
        select_query.limit.return_value = select_query
        select_query.execute.return_value = _ExecuteResult([{'id': 'm1', 'weight': 0.25, 'hit_count': 1}])
        update_query = MagicMock()
        table.update.return_value = update_query
        update_query.eq.return_value = update_query

        apply_silent_confirm(
            self.tenant,
            merchant_key='lawson',
            category_code='food.grocery',
        )
        payload = table.update.call_args.args[0]
        self.assertEqual(payload['last_source'], 'silent_confirm')
        self.assertAlmostEqual(payload['weight'], 0.75)


if __name__ == '__main__':
    unittest.main()
