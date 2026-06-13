import unittest

from services.usage_config import get_free_tier_limits
from services.usage_repository import current_jst_year_month


class TestUsageConfig(unittest.TestCase):
    def test_free_tier_defaults(self):
        limits = get_free_tier_limits()
        self.assertEqual(limits.monthly_total, 300)
        self.assertEqual(limits.monthly_receipt_analyses, 100)
        self.assertEqual(limits.rate_per_minute, 10)
        self.assertEqual(limits.rate_per_day, 100)
        self.assertEqual(limits.max_text_words, 1000)
        self.assertEqual(limits.max_image_bytes, 10 * 1024 * 1024)

    def test_jst_year_month_format(self):
        value = current_jst_year_month()
        self.assertRegex(value, r'^\d{4}-\d{2}$')


if __name__ == '__main__':
    unittest.main()
