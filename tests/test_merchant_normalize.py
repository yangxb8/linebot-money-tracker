import unittest

from services.merchant_normalize import (
    heuristic_merchant_from_description,
    is_generic_merchant_text,
    normalize_merchant_key,
    reset_merchant_alias_cache_for_tests,
    strip_branch_suffix,
)


class TestMerchantNormalize(unittest.TestCase):
    def setUp(self):
        reset_merchant_alias_cache_for_tests()

    def test_alias_seven_eleven(self):
        self.assertEqual(normalize_merchant_key('セブン-イレブン'), 'seven_eleven')
        self.assertEqual(heuristic_merchant_from_description('7-ELEVEN おにぎり'), 'seven_eleven')

    def test_strip_branch_suffix(self):
        self.assertEqual(strip_branch_suffix('スターバックス 渋谷店'), 'スターバックス')

    def test_generic_denylist(self):
        self.assertTrue(is_generic_merchant_text('食費'))
        self.assertTrue(is_generic_merchant_text('買い物'))
        self.assertIsNone(normalize_merchant_key('食費'))
        self.assertIsNone(heuristic_merchant_from_description('食費 5000円'))

    def test_starbucks_alias(self):
        self.assertEqual(normalize_merchant_key('スターバックス'), 'starbucks')


if __name__ == '__main__':
    unittest.main()
