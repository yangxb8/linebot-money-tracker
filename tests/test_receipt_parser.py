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

    def test_parse_leading_amount_cjk_shorthand(self):
        items = parse_text_for_expenses('861便利店')
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 861.0)
        self.assertEqual(items[0]['currency'], 'JPY')
        self.assertIn('便利店', items[0]['description'])

    def test_parse_leading_amount_cjk_with_space(self):
        items = parse_text_for_expenses('861 便利店')
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 861.0)

    def test_parse_trailing_amount_cjk_shorthand(self):
        items = parse_text_for_expenses('1200ランチ')
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 1200.0)
        self.assertIn('ランチ', items[0]['description'])

    def test_parse_trailing_amount_mixed_script(self):
        items = parse_text_for_expenses('tokyo game show门票 6440')
        self.assertEqual(len(items), 1)
        self.assertAlmostEqual(items[0]['amount'], 6440.0)
        self.assertEqual(items[0]['currency'], 'JPY')
        self.assertIn('门票', items[0]['description'])

    def test_rejects_question_about_brand(self):
        items = parse_text_for_expenses('什么是861便利店？')
        self.assertEqual(items, [])

    def test_rejects_multi_line_receipt_text(self):
        ocr = '''まいばすけっと
ジャイアントコーンショ 159※
合計 ¥321'''
        self.assertEqual(parse_text_for_expenses(ocr), [])


if __name__ == '__main__':
    unittest.main()
