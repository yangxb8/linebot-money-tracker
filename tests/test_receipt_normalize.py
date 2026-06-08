import unittest

from services.receipt_normalize import (
    extract_merchant_name,
    extract_receipt_totals,
    finalize_receipt_extraction,
    normalize_receipt_items,
    try_total_only_fallback,
)
from services.receipt_parser import parse_text_for_expenses

MY_BASKET_OCR = '''まいばすけっと
瀬ヶ崎３丁目店
TEL 048-621-5482
ジャイアントコーンショ 159※
エッセルカップバニラ 139※ A
小計 ¥298
外税 8%対象額 ¥298
外税 8% ¥23
合計 ¥321
iD支払 ¥321
お釣り ¥0'''


class TestReceiptTotals(unittest.TestCase):
    def test_extract_my_basket_totals(self):
        totals = extract_receipt_totals(MY_BASKET_OCR)
        self.assertEqual(totals.subtotal, 298)
        self.assertEqual(totals.tax, 23)
        self.assertEqual(totals.grand_total, 321)
        self.assertEqual(totals.cash_paid, 321)

    def test_extract_merchant_name(self):
        self.assertEqual(extract_merchant_name(MY_BASKET_OCR), 'まいばすけっと')


class TestReceiptNormalize(unittest.TestCase):
    def test_allocates_tax_proportionally_for_my_basket(self):
        items = parse_text_for_expenses(MY_BASKET_OCR)
        normalized = normalize_receipt_items(items, MY_BASKET_OCR)
        self.assertEqual(len(normalized), 2)
        total = sum(item['amount'] for item in normalized)
        self.assertAlmostEqual(total, 321.0, delta=0.02)
        self.assertGreater(normalized[0]['amount'], 159.0)
        self.assertGreater(normalized[1]['amount'], 139.0)

    def test_allocates_discount_proportionally(self):
        ocr = '''スーパー
りんご 1000円
バナナ 500円
小計 ¥1500
値引 ¥150
合計 ¥1350
現金支払 ¥1350'''
        items = parse_text_for_expenses(ocr)
        normalized = normalize_receipt_items(items, ocr)
        self.assertEqual(len(normalized), 2)
        self.assertAlmostEqual(sum(item['amount'] for item in normalized), 1350.0, delta=0.02)

    def test_total_only_fallback(self):
        ocr = '''まいばすけっと
瀬ヶ崎店
合計 ¥321'''
        items = try_total_only_fallback(ocr)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['description'], 'まいばすけっと')
        self.assertAlmostEqual(items[0]['amount'], 321.0)

    def test_finalize_uses_fallback_when_no_line_items(self):
        ocr = '''コンビニ
合計 ¥600'''
        items = finalize_receipt_extraction([], ocr)
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 600.0)

    def test_skips_normalization_for_simple_text(self):
        items = [{'description': 'Lunch', 'amount': 120.0, 'currency': 'THB'}]
        result = normalize_receipt_items(items, 'Lunch 120 THB at cafe')
        self.assertEqual(result[0]['amount'], 120.0)


if __name__ == '__main__':
    unittest.main()
