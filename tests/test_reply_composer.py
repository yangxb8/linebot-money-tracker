import unittest

from services.reply_composer import compose_confirmation_reply, join_sections


class TestReplyComposer(unittest.TestCase):
    def test_join_sections_skips_empty(self):
        self.assertEqual(join_sections(['A', '', 'B']), 'A\n\nB')

    def test_single_item_compact(self):
        text = compose_confirmation_reply(
            [
                {
                    'description': 'Lunch',
                    'amount': 1200,
                    'currency': 'JPY',
                    'category_guess_path': '食費 > 外食',
                }
            ],
            language='ja',
        )
        self.assertIn('✅ Lunch ¥1200', text)
        self.assertIn('食費 > 外食', text)
        self.assertNotIn('このメッセージに返信', text or '')

    def test_multi_item_subtotals_default(self):
        text = compose_confirmation_reply(
            [
                {
                    'description': 'Coffee',
                    'amount': 450,
                    'currency': 'JPY',
                    'category_guess_path': '食費 > 外食',
                },
                {
                    'description': 'Soap',
                    'amount': 300,
                    'currency': 'JPY',
                    'category_guess_path': '生活 > 日用品',
                },
            ],
            language='ja',
        )
        self.assertIn('合計 ¥750（2件）', text)
        self.assertIn('食費 > 外食 ¥450', text)
        self.assertIn('生活 > 日用品 ¥300', text)
        self.assertNotIn('Coffee', text)

    def test_multi_item_details_when_enabled(self):
        text = compose_confirmation_reply(
            [
                {
                    'description': 'Coffee',
                    'amount': 450,
                    'currency': 'JPY',
                    'category_guess_path': '食費 > 外食',
                },
                {
                    'description': 'Soap',
                    'amount': 300,
                    'currency': 'JPY',
                    'category_guess_path': '生活 > 日用品',
                },
            ],
            language='ja',
            show_item_details=True,
        )
        self.assertIn('1) Coffee ¥450', text)
        self.assertIn('2) Soap ¥300', text)
