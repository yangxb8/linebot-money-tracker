import unittest

from services.confirmation_i18n import format_expense_confirmation, item_number_label, t
from services.help_intent import help_reply, is_help_request_obvious


class TestConfirmationI18n(unittest.TestCase):
    def test_emoji_item_numbers(self):
        self.assertEqual(item_number_label(1), '1️⃣')
        self.assertEqual(item_number_label(3), '3️⃣')
        self.assertEqual(item_number_label(11), '11)')

    def test_compact_single_item(self):
        text = format_expense_confirmation(
            [
                {
                    'description': 'Coffee',
                    'amount': 450,
                    'currency': 'JPY',
                    'category_guess_path': '食費',
                }
            ],
            language='ja',
        )
        self.assertIn('✅ Coffee ¥450', text)
        self.assertNotIn('このメッセージに返信', text or '')

    def test_english_compact(self):
        text = format_expense_confirmation(
            [{'description': 'Lunch', 'amount': 120, 'currency': 'JPY', 'category_guess_path': 'Food'}],
            language='en',
        )
        self.assertIn('✅ Lunch ¥120', text)
        self.assertIn('Food', text)

    def test_multi_item_subtotals(self):
        text = format_expense_confirmation(
            [
                {'description': 'Coffee', 'amount': 450, 'currency': 'JPY', 'category_guess_path': '食費'},
                {'description': 'Tea', 'amount': 300, 'currency': 'JPY', 'category_guess_path': '食費'},
            ],
            language='ja',
        )
        self.assertIn('合計 ¥750（2件）', text)
        self.assertIn('食費 ¥750', text)


class TestHelpIntent(unittest.TestCase):
    def test_help_request_detected(self):
        self.assertTrue(is_help_request_obvious('How do I delete an expense?'))

    def test_help_reply_localized(self):
        self.assertIn('YES', help_reply('en'))
        self.assertIn('YES', help_reply('ja'))
        self.assertIn('YES', help_reply('zh'))

    def test_help_strings_exist(self):
        self.assertIn('Reply to the expense confirmation', t('en', 'help_edit'))
