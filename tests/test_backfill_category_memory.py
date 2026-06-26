import unittest
from unittest.mock import MagicMock, patch

from scripts.backfill_category_memory import collect_backfill_rows


class TestBackfillCategoryMemory(unittest.TestCase):
    @patch('scripts.backfill_category_memory.is_supabase_configured', return_value=True)
    @patch('scripts.backfill_category_memory.get_supabase_client')
    @patch('scripts.backfill_category_memory._category_code_for_expense', return_value='food.grocery')
    def test_prefers_metadata_store_name_over_product_description(
        self,
        _category_code,
        get_client,
        _configured,
    ):
        client = MagicMock()
        get_client.return_value = client
        client.table.return_value.select.return_value.is_.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    'tenant_type': 'user',
                    'tenant_id': 'u1',
                    'logged_by_line_user_id': 'u1',
                    'description': '牛乳',
                    'category_node_id': 'node-1',
                    'created_at': '2026-01-01T00:00:00Z',
                    'metadata': {'store_name': 'イオン'},
                },
                {
                    'tenant_type': 'user',
                    'tenant_id': 'u1',
                    'logged_by_line_user_id': 'u1',
                    'description': '食パン',
                    'category_node_id': 'node-1',
                    'created_at': '2026-01-02T00:00:00Z',
                    'metadata': {'store_name': 'イオン'},
                },
            ]
        )

        rows = collect_backfill_rows()
        self.assertIn(('user', 'u1', 'aeon'), rows)
        self.assertEqual(rows[('user', 'u1', 'aeon')]['category_code'], 'food.grocery')


if __name__ == '__main__':
    unittest.main()
