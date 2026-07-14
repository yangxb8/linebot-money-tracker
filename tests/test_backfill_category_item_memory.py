import unittest
from unittest.mock import MagicMock, patch

from scripts.backfill_category_item_memory import collect_backfill_rows, upsert_rows


class TestBackfillCategoryItemMemory(unittest.TestCase):
    @patch('scripts.backfill_category_item_memory.is_supabase_configured', return_value=True)
    @patch('scripts.backfill_category_item_memory.get_supabase_client')
    @patch(
        'scripts.backfill_category_item_memory.merchant_key_from_expense_row',
        return_value='shimachu',
    )
    @patch(
        'scripts.backfill_category_item_memory.normalize_item_key',
        return_value='陶器プランター',
    )
    @patch(
        'scripts.backfill_category_item_memory._category_code_for_expense',
        return_value='living.plants',
    )
    def test_collect_only_store_name_expenses(
        self,
        _code,
        _item,
        _merchant,
        get_client,
        _configured,
    ):
        client = MagicMock()
        get_client.return_value = client
        table = MagicMock()
        client.table.return_value = table
        query = MagicMock()
        table.select.return_value = query
        query.is_.return_value = query
        query.order.return_value = query
        query.execute.return_value = MagicMock(
            data=[
                {
                    'tenant_type': 'user',
                    'tenant_id': 'u1',
                    'logged_by_line_user_id': 'u1',
                    'description': '陶器プランター',
                    'category_node_id': 'n1',
                    'created_at': '2026-01-01',
                    'metadata': {'store_name': '島忠ホームズ'},
                },
                {
                    'tenant_type': 'user',
                    'tenant_id': 'u1',
                    'logged_by_line_user_id': 'u1',
                    'description': 'ラテ',
                    'category_node_id': 'n2',
                    'created_at': '2026-01-02',
                    'metadata': {},
                },
            ]
        )
        rows = collect_backfill_rows()
        self.assertEqual(len(rows), 1)
        payload = next(iter(rows.values()))
        self.assertEqual(payload['memory_kind'], 'store_item')
        self.assertEqual(payload['last_source'], 'backfill')

    def test_dry_run_does_not_write(self):
        count = upsert_rows(
            {
                ('user', 'u1', 'shimachu', '陶器プランター'): {
                    'tenant_type': 'user',
                    'tenant_id': 'u1',
                    'memory_kind': 'store_item',
                    'merchant_key': 'shimachu',
                    'item_key': '陶器プランター',
                    'category_code': 'living.plants',
                    'weight': 0.25,
                    'last_source': 'backfill',
                }
            },
            dry_run=True,
        )
        self.assertEqual(count, 1)


if __name__ == '__main__':
    unittest.main()
