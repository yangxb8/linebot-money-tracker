import unittest
from unittest.mock import MagicMock, patch

from services.usage_limit_i18n import usage_limit_message
from services.usage_limiter import LimitDenyReason, format_denial_reply


class TestUsageLimitI18n(unittest.TestCase):
    def test_all_keys_ja(self):
        for key in (
            'payload_too_large_text',
            'payload_too_large_image',
            'user_rate_limit_minute',
            'user_rate_limit_day',
            'user_quota_monthly',
            'user_receipt_quota_monthly',
        ):
            text = usage_limit_message('ja', key, max_words='1000', max_mb='10')
            self.assertTrue(len(text) > 5)

    def test_denial_mapping(self):
        text = format_denial_reply('en', LimitDenyReason.QUOTA_MONTHLY)
        self.assertIn('month', text.lower())


if __name__ == '__main__':
    unittest.main()
