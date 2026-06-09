import unittest
from decimal import Decimal

from services.receipt_validate import validate_receipt_items

MY_BASKET_OCR = '''まいばすけっと
ジャイアントコーンショ 159※
エッセルカップバニラ 139※ A
小計 ¥298
外税 8% ¥23
合計 ¥321
iD支払 ¥321'''

GARBAGE_ITEMS = [
    {'description': 'i EONS: ********', 'amount': 30299.96, 'currency': 'JPY'},
    {'description': 'エッセルカップバニラ  A', 'amount': 0.06, 'currency': 'JPY'},
    {'description': 'カード会社 dカード', 'amount': 13.96, 'currency': 'JPY'},
]


class TestReceiptValidate(unittest.TestCase):
    def test_rejects_garbage_vision_output(self):
        self.assertIsNone(validate_receipt_items(GARBAGE_ITEMS, MY_BASKET_OCR))

    def test_accepts_valid_normalized_items(self):
        items = [
            {'description': 'ジャイアントコーンショ', 'amount': 171.27, 'currency': 'JPY'},
            {'description': 'エッセルカップバニラ', 'amount': 149.73, 'currency': 'JPY'},
        ]
        result = validate_receipt_items(items, MY_BASKET_OCR)
        self.assertEqual(len(result), 2)

    def test_rejects_sum_mismatch(self):
        items = [
            {'description': 'お茶', 'amount': 100.0, 'currency': 'JPY'},
            {'description': 'コーヒー', 'amount': 100.0, 'currency': 'JPY'},
        ]
        self.assertIsNone(validate_receipt_items(items, MY_BASKET_OCR))

    def test_rejects_partial_parse_below_subtotal(self):
        ocr = '''島忠
小計 ¥5,723
買上点数 10
合計 ¥5,723'''
        items = [
            {'description': 'フリーザーバッグ', 'amount': 249.0, 'currency': 'JPY'},
            {'description': 'アルミホイル', 'amount': 140.0, 'currency': 'JPY'},
        ]
        self.assertIsNone(validate_receipt_items(items, ocr))

    def test_rejects_item_count_mismatch(self):
        ocr = '''島忠
買上点数 10
合計 ¥5,723'''
        items = [{'description': 'item', 'amount': 5723.0, 'currency': 'JPY'}]
        self.assertIsNone(validate_receipt_items(items, ocr))

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


if __name__ == '__main__':
    unittest.main()
