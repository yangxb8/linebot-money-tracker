import unittest

from services.category_taxonomy import (
    UNKNOWN_CODE,
    category_id_for_code,
    format_category_path,
    load_category_taxonomy,
    resolve_code,
)


class TestCategoryTaxonomy(unittest.TestCase):
    def test_loads_unknown_node(self):
        taxonomy = load_category_taxonomy()
        self.assertIn(UNKNOWN_CODE, taxonomy)
        self.assertEqual(taxonomy[UNKNOWN_CODE].name_ja, '不明')

    def test_legacy_l3_code_maps_to_l2_parent(self):
        node = resolve_code('food.dining.cafe')
        self.assertEqual(node.level, 2)
        self.assertEqual(node.code, 'food.dining')
        self.assertEqual(node.l1_id, category_id_for_code('food'))
        self.assertEqual(node.l2_id, category_id_for_code('food.dining'))
        self.assertIsNone(node.l3_id)
        self.assertEqual(format_category_path(node), '食費 > 外食')

    def test_taxonomy_max_depth_is_two(self):
        taxonomy = load_category_taxonomy()
        self.assertTrue(all(node.level <= 2 for node in taxonomy.values()))

    def test_resolve_l2_denormalized_ancestors(self):
        node = resolve_code('transport.transit')
        self.assertEqual(node.level, 2)
        self.assertEqual(node.l1_id, category_id_for_code('transport'))
        self.assertEqual(node.l2_id, node.id)
        self.assertIsNone(node.l3_id)

    def test_invalid_code_falls_back_to_unknown(self):
        node = resolve_code('not.a.real.code')
        self.assertEqual(node.code, UNKNOWN_CODE)

    def test_deterministic_ids_match_namespace(self):
        self.assertEqual(
            category_id_for_code('food'),
            '249350c8-4b24-5117-a515-9ef3988701de',
        )


if __name__ == '__main__':
    unittest.main()
