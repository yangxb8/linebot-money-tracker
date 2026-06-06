import unittest

from services.receipt_parser import parse_text_for_expenses


class TestReceiptParser(unittest.TestCase):
    def test_parse_simple_text_with_currency(self):
        items = parse_text_for_expenses('Lunch 120 THB at Cafe')
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 120.0)
        self.assertIn('Lunc', items[0]['description'][:4].title() or items[0]['description'])

    def test_parse_with_symbol(self):
        items = parse_text_for_expenses('Paid $12.50 for taxi')
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 12.5)

    def test_parse_japanese_yen_suffix(self):
        items = parse_text_for_expenses('コーヒー 450円')
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 450.0)
        self.assertEqual(items[0]['currency'], 'JPY')

    def test_parse_japanese_yen_prefix(self):
        items = parse_text_for_expenses('合計 ¥1,280')
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 1280.0)
        self.assertEqual(items[0]['currency'], 'JPY')

    def test_parse_full_width_digits(self):
        items = parse_text_for_expenses('お茶 ３００円')
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 300.0)

    def test_parse_multi_line_japanese_receipt_sample(self):
        from pathlib import Path

        sample = Path('specs/002-expense-intent-analysis/samples/japanese_receipt.ocr.txt').read_text(encoding='utf-8')
        items = parse_text_for_expenses(sample)
        self.assertGreaterEqual(len(items), 4)
        amounts = [item['amount'] for item in items]
        self.assertIn(600.0, amounts)


if __name__ == '__main__':
    unittest.main()
