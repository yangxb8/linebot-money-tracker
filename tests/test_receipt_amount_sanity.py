import unittest

from services.receipt_normalize import normalize_receipt_items
from services.receipt_parser import parse_text_for_expenses
from services.receipt_validate import validate_receipt_items

MY_BASKET_OCR = '''まいばすけっと
ジャイアントコーンショ 159※
エッセルカップバニラ 139※ A
小計 ¥298
外税 8% ¥23
合計 ¥321
iD支払 ¥321'''

MY_BASKET_WITH_CARD_SLIP = MY_BASKET_OCR + '''
i EONS: ********30299.96
エッセルカップバニラ  A 0.06
カード会社 dカード 13.96'''


class TestReceiptAmountSanity(unittest.TestCase):
    def test_my_basket_not_scaled_to_card_slip_total(self):
        items = parse_text_for_expenses(MY_BASKET_OCR)
        normalized = normalize_receipt_items(items, MY_BASKET_OCR)
        self.assertEqual(len(normalized), 2)
        total = sum(item['amount'] for item in normalized)
        self.assertAlmostEqual(total, 321.0, delta=2.0)
        self.assertLess(normalized[0]['amount'], 500)

    def test_rejects_insane_scaled_amounts(self):
        items = [
            {'description': 'コーン', 'amount': 16200.22, 'currency': 'JPY'},
            {'description': 'カップ', 'amount': 14162.78, 'currency': 'JPY'},
        ]
        self.assertIsNone(validate_receipt_items(items, MY_BASKET_WITH_CARD_SLIP))
