import unittest
from decimal import Decimal

from services.receipt_validate import _garbage_reason, validate_receipt_items

GARBAGE_ITEMS = [
    {'description': 'i EONS: ********', 'amount': 30299.96, 'currency': 'JPY'},
    {'description': 'エッセルカップバニラ  A', 'amount': 0.06, 'currency': 'JPY'},
    {'description': 'カード会社 dカード', 'amount': 13.96, 'currency': 'JPY'},
]


class TestReceiptValidate(unittest.TestCase):
    def test_rejects_garbage_items_without_total(self):
        self.assertIsNone(validate_receipt_items(GARBAGE_ITEMS))

    def test_accepts_valid_items_without_total(self):
        items = [
            {'description': 'ジャイアントコーンショ', 'amount': 171.27, 'currency': 'JPY'},
            {'description': 'エッセルカップバニラ', 'amount': 149.73, 'currency': 'JPY'},
        ]
        result = validate_receipt_items(items)
        self.assertEqual(len(result), 2)

    def test_accepts_items_matching_llm_total(self):
        items = [
            {'description': 'ジャイアントコーンショ', 'amount': 171.0, 'currency': 'JPY'},
            {'description': 'エッセルカップバニラ', 'amount': 150.0, 'currency': 'JPY'},
        ]
        result = validate_receipt_items(items, receipt_total=Decimal('321'))
        self.assertEqual(len(result), 2)

    def test_rejects_items_not_matching_llm_total(self):
        items = [
            {'description': 'お茶', 'amount': 100.0, 'currency': 'JPY'},
            {'description': 'コーヒー', 'amount': 100.0, 'currency': 'JPY'},
        ]
        self.assertIsNone(validate_receipt_items(items, receipt_total=Decimal('321')))

    def test_logs_dropped_garbage_and_keeps_matching_items(self):
        items = [
            {'description': 'お茶', 'amount': 171.0, 'currency': 'JPY'},
            {'description': 'コーヒー', 'amount': 150.0, 'currency': 'JPY'},
            {'description': 'カード会社 dカード', 'amount': 321.0, 'currency': 'JPY'},
        ]
        result = validate_receipt_items(items, receipt_total=Decimal('321'))
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)

    def test_accepts_single_kanji_product_name(self):
        """Lopia-style: 桃 alone is a valid product line, not garbage."""
        items = [
            {'description': '日清ヨーク ピ', 'amount': 237.0, 'currency': 'JPY'},
            {'description': 'ウンジンアロエ', 'amount': 516.0, 'currency': 'JPY'},
            {'description': '明治 R-1 ド', 'amount': 248.0, 'currency': 'JPY'},
            {'description': '桃', 'amount': 1620.0, 'currency': 'JPY'},
        ]
        self.assertIsNone(_garbage_reason(items[3]))
        result = validate_receipt_items(items, receipt_total=Decimal('2621'))
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[3]['description'], '桃')

    def test_rejects_single_ascii_noise_description(self):
        items = [{'description': 'A', 'amount': 100.0, 'currency': 'JPY'}]
        self.assertEqual(_garbage_reason(items[0]), 'short_ascii_description')
        self.assertIsNone(validate_receipt_items(items, receipt_total=Decimal('100')))


if __name__ == '__main__':
    unittest.main()
