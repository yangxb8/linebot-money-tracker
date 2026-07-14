import unittest

from services.item_normalize import normalize_item_key


class TestItemNormalize(unittest.TestCase):
    def test_planter_strips_size_model(self):
        key = normalize_item_key('園芸 陶器プランターW2 A')
        self.assertIsNotNone(key)
        assert key is not None
        self.assertIn('プランター', key)
        self.assertNotIn('W2', key.upper())
        self.assertFalse(key.endswith('_a') or key.endswith('A'))

    def test_toilet_paper_strips_roll(self):
        key = normalize_item_key('シャワートイレ用パルプ ロールダブル')
        self.assertIsNotNone(key)
        assert key is not None
        self.assertIn('パルプ', key)
        self.assertNotIn('ロール', key)

    def test_milk_simple(self):
        self.assertEqual(normalize_item_key('牛乳'), '牛乳')

    def test_generic_returns_none(self):
        self.assertIsNone(normalize_item_key('商品'))
        self.assertIsNone(normalize_item_key('不明'))
        self.assertIsNone(normalize_item_key(''))


if __name__ == '__main__':
    unittest.main()
