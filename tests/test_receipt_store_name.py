import unittest

from services.receipt_store_name import propagate_receipt_store_name


class TestPropagateReceiptStoreName(unittest.TestCase):
    def test_propagates_receipt_level_store_to_all_lines(self):
        items = [
            {'description': '牛乳', 'amount': 198, 'currency': 'JPY'},
            {'description': '食パン', 'amount': 128, 'currency': 'JPY'},
        ]
        result = propagate_receipt_store_name(items, 'イオン')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['store_name'], 'イオン')
        self.assertEqual(result[1]['store_name'], 'イオン')
        self.assertEqual(result[0]['description'], '牛乳')

    def test_null_when_store_absent(self):
        items = [{'description': 'Coffee', 'amount': 450, 'currency': 'JPY'}]
        result = propagate_receipt_store_name(items, None)
        self.assertNotIn('store_name', result[0])

    def test_null_when_empty_store(self):
        items = [{'description': 'Coffee', 'amount': 450, 'currency': 'JPY'}]
        result = propagate_receipt_store_name(items, '   ')
        self.assertNotIn('store_name', result[0])

    def test_null_when_item_store_conflicts_with_receipt(self):
        items = [
            {'description': '牛乳', 'amount': 198, 'currency': 'JPY', 'store_name': 'イオン'},
            {'description': '食パン', 'amount': 128, 'currency': 'JPY', 'store_name': 'セブン'},
        ]
        result = propagate_receipt_store_name(items, 'イオン')
        self.assertNotIn('store_name', result[0])
        self.assertNotIn('store_name', result[1])


if __name__ == '__main__':
    unittest.main()
