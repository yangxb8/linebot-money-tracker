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
        self.assertGreaterEqual(len(items), 3)
        amounts = [item['amount'] for item in items]
        self.assertIn(150.0, amounts)
        self.assertIn(198.0, amounts)

    def test_parse_shimachu_vision_ocr_compound_line(self):
        from pathlib import Path

        sample = Path(
            'specs/002-expense-intent-analysis/samples/shimachu_receipt.vision_ocr.txt'
        ).read_text(encoding='utf-8')
        items = parse_text_for_expenses(sample)
        amounts = sorted(item['amount'] for item in items)
        self.assertEqual(len(items), 10)
        self.assertEqual(sum(item['amount'] for item in items), 5723.0)
        self.assertIn(249.0, amounts)
        self.assertIn(140.0, amounts)
        self.assertIn(327.0, amounts)
        self.assertIn(877.0, amounts)
        self.assertNotIn('P2111200001860', items[1]['description'])

    def test_parse_shimachu_multiline_wrapped_items(self):
        from pathlib import Path

        sample = Path('specs/002-expense-intent-analysis/samples/shimachu_receipt.ocr.txt').read_text(
            encoding='utf-8'
        )
        items = parse_text_for_expenses(sample)
        amounts = sorted(item['amount'] for item in items)
        self.assertGreaterEqual(len(items), 5)
        self.assertIn(249.0, amounts)
        self.assertIn(140.0, amounts)
        self.assertIn(648.0, amounts)
        descriptions = ' '.join(item['description'] for item in items)
        self.assertIn('フリーザーバッグ', descriptions)
        self.assertIn('ジッパー', descriptions)

    def test_parse_my_basket_style_receipt(self):
        ocr = '''まいばすけっと
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
        items = parse_text_for_expenses(ocr)
        descriptions = [item['description'] for item in items]
        amounts = [item['amount'] for item in items]
        self.assertEqual(len(items), 2)
        self.assertIn(159.0, amounts)
        self.assertIn(139.0, amounts)
        self.assertTrue(any('コーン' in desc for desc in descriptions))
        self.assertTrue(all(item['currency'] == 'JPY' for item in items))


if __name__ == '__main__':
    unittest.main()
