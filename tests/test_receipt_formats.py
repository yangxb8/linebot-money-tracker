import unittest
from pathlib import Path

from services.receipt_normalize import finalize_receipt_extraction, normalize_receipt_items
from services.receipt_parser import parse_text_for_expenses
from services.receipt_validate import validate_receipt_items

SAMPLES = Path('specs/002-expense-intent-analysis/samples')


class TestReceiptFormats(unittest.TestCase):
    def _load(self, name: str) -> str:
        return (SAMPLES / name).read_text(encoding='utf-8')

    def test_yaoko_parses_five_items(self):
        ocr = self._load('yaoko_receipt.ocr.txt')
        items = parse_text_for_expenses(ocr)
        self.assertEqual(len(items), 5)
        self.assertEqual(sum(item['amount'] for item in items), 1540.0)
        normalized = normalize_receipt_items(items, ocr)
        self.assertAlmostEqual(sum(item['amount'] for item in normalized), 1663.0, delta=2.0)

    def test_shigezo_includes_bag_and_keeps_total(self):
        ocr = self._load('shigezo_receipt.ocr.txt')
        items = parse_text_for_expenses(ocr)
        self.assertEqual(len(items), 4)
        amounts = [item['amount'] for item in items]
        self.assertIn(3.0, amounts)
        normalized = normalize_receipt_items(items, ocr)
        self.assertAlmostEqual(sum(item['amount'] for item in normalized), 556.0, delta=2.0)

    def test_daiso_line_totals_with_qty_detail(self):
        ocr = self._load('daiso_receipt.ocr.txt')
        items = parse_text_for_expenses(ocr)
        self.assertEqual(len(items), 4)
        amounts = sorted(item['amount'] for item in items)
        self.assertEqual(amounts, [100.0, 100.0, 600.0, 600.0])
        normalized = normalize_receipt_items(items, ocr)
        self.assertAlmostEqual(sum(item['amount'] for item in normalized), 1538.0, delta=2.0)

    def test_ikea_parses_product_blocks(self):
        ocr = self._load('ikea_receipt.ocr.txt')
        items = parse_text_for_expenses(ocr)
        self.assertEqual(len(items), 6)
        self.assertAlmostEqual(sum(item['amount'] for item in items), 2770.0, delta=0.01)
        self.assertTrue(any('ドリンク' in item['description'] for item in items))

    def test_restaurant_tabular_rows(self):
        ocr = self._load('restaurant_receipt.ocr.txt')
        items = parse_text_for_expenses(ocr)
        self.assertEqual(len(items), 4)
        self.assertAlmostEqual(sum(item['amount'] for item in items), 2050.0, delta=0.01)

    def test_yaoko_validation_passes_after_normalize(self):
        ocr = self._load('yaoko_receipt.ocr.txt')
        items = finalize_receipt_extraction(parse_text_for_expenses(ocr), ocr)
        self.assertIsNotNone(validate_receipt_items(items, ocr))

    def test_points_section_not_parsed_as_items(self):
        ocr = self._load('yaoko_receipt.ocr.txt')
        items = parse_text_for_expenses(ocr)
        descriptions = ' '.join(item['description'] for item in items)
        self.assertNotIn('ポイント', descriptions)


if __name__ == '__main__':
    unittest.main()
