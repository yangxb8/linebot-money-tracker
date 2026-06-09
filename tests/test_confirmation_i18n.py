import unittest

from services.confirmation_i18n import format_expense_confirmation, item_number_label


class TestConfirmationI18n(unittest.TestCase):
    def test_emoji_item_numbers(self):
        self.assertEqual(item_number_label(1), '1️⃣')
        self.assertEqual(item_number_label(3), '3️⃣')
        self.assertEqual(item_number_label(11), '11)')

    def test_instructions_once_at_top(self):
        text = format_expense_confirmation(
            [
                {
                    'description': 'Coffee',
                    'amount': 450,
                    'currency': 'JPY',
                    'category_guess_path': '食費',
                    'category_alternative_paths': ['娯楽'],
                },
                {
                    'description': 'Tea',
                    'amount': 300,
                    'currency': 'JPY',
                    'category_guess_path': '食費',
                    'category_alternative_paths': ['不明'],
                },
            ],
            language='ja',
        )
        self.assertIsNotNone(text)
        self.assertEqual(text.count('このメッセージに返信'), 1)
        self.assertIn('1️⃣ Coffee:', text)
        self.assertIn('2️⃣ Tea:', text)
        self.assertIn('  1) 娯楽', text)

    def test_english_header(self):
        text = format_expense_confirmation(
            [{'description': 'Lunch', 'amount': 120, 'currency': 'JPY'}],
            language='en',
        )
        self.assertIn('Detected expense(s):', text)
        self.assertIn('1️⃣ Lunch:', text)
