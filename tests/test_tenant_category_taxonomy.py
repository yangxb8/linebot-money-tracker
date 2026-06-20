import unittest
from unittest.mock import patch

from services.category_taxonomy import (
    UNKNOWN_CODE,
    _build_taxonomy_from_db_rows,
    load_category_taxonomy,
    reset_category_taxonomy_cache_for_tests,
    resolve_code,
)
from services.tenant_context import TenantContext


class TestTenantCategoryTaxonomy(unittest.TestCase):
    def setUp(self):
        reset_category_taxonomy_cache_for_tests()

    def tearDown(self):
        reset_category_taxonomy_cache_for_tests()

    def test_build_taxonomy_from_db_rows(self):
        l1_id = '11111111-1111-1111-1111-111111111111'
        l2_id = '22222222-2222-2222-2222-222222222222'
        unknown_id = '33333333-3333-3333-3333-333333333333'
        rows = [
            {
                'id': unknown_id,
                'code': 'unknown',
                'name_ja': '不明',
                'level': 1,
                'parent_id': None,
                'sort_order': 99,
            },
            {
                'id': l1_id,
                'code': 'food',
                'name_ja': '食費',
                'level': 1,
                'parent_id': None,
                'sort_order': 1,
            },
            {
                'id': l2_id,
                'code': 'food.grocery',
                'name_ja': '食料品',
                'level': 2,
                'parent_id': l1_id,
                'sort_order': 1,
            },
        ]
        taxonomy = _build_taxonomy_from_db_rows(rows)
        self.assertIn('food.grocery', taxonomy)
        node = taxonomy['food.grocery']
        self.assertEqual(node.l1_id, l1_id)
        self.assertEqual(node.l2_id, l2_id)
        self.assertEqual(node.path_names, ('食費', '食料品'))

    @patch('services.category_taxonomy.is_supabase_configured', return_value=True)
    @patch('services.category_taxonomy._load_tenant_taxonomy_from_db')
    def test_load_category_taxonomy_uses_tenant_rows(
        self,
        mock_load_tenant,
        _mock_configured,
    ):
        l1_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        mock_load_tenant.return_value = _build_taxonomy_from_db_rows(
            [
                {
                    'id': l1_id,
                    'code': 'custom.abc',
                    'name_ja': 'ペット',
                    'level': 1,
                    'parent_id': None,
                    'sort_order': 1,
                },
                {
                    'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
                    'code': UNKNOWN_CODE,
                    'name_ja': '不明',
                    'level': 1,
                    'parent_id': None,
                    'sort_order': 99,
                },
            ]
        )
        tenant = TenantContext.personal('U123')
        taxonomy = load_category_taxonomy(tenant.tenant_type, tenant.tenant_id)
        self.assertIn('custom.abc', taxonomy)
        self.assertEqual(resolve_code('custom.abc', tenant).name_ja, 'ペット')
        mock_load_tenant.assert_called_once_with('user', 'U123')

    @patch('services.category_taxonomy.is_supabase_configured', return_value=True)
    @patch('services.category_taxonomy._load_tenant_taxonomy_from_db', return_value=None)
    def test_load_category_taxonomy_falls_back_to_yaml(self, _mock_load, _mock_configured):
        tenant = TenantContext.personal('U123')
        taxonomy = load_category_taxonomy(tenant.tenant_type, tenant.tenant_id)
        self.assertIn('food', taxonomy)


if __name__ == '__main__':
    unittest.main()
