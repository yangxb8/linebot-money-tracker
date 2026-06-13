import unittest
from unittest.mock import MagicMock, patch

from services.tenant_context import TenantContext
from services.usage_limiter import (
    LimitDenyReason,
    check_payload_image,
    check_payload_text,
    count_words,
    format_denial_reply,
    prepare_inbound_usage,
    resolve_billing_user,
)
from services.usage_metering import UsageBillingContext


class TestUsageLimiter(unittest.TestCase):
    def test_count_words(self):
        self.assertEqual(count_words('Lunch 1200 yen'), 3)

    def test_payload_text_limit(self):
        words = ' '.join(['word'] * 1001)
        self.assertEqual(check_payload_text(words), LimitDenyReason.PAYLOAD_TEXT)
        self.assertIsNone(check_payload_text('Lunch 1200 yen'))

    def test_payload_image_limit(self):
        self.assertEqual(check_payload_image(b'x' * (10 * 1024 * 1024 + 1)), LimitDenyReason.PAYLOAD_IMAGE)
        self.assertIsNone(check_payload_image(b'small'))

    def test_format_denial_reply(self):
        text = format_denial_reply('en', LimitDenyReason.RATE_MINUTE)
        self.assertIn('too quickly', text)

    @patch('services.usage_limiter.has_quota_headroom', return_value=True)
    def test_resolve_billing_user_sender(self, _headroom):
        tenant = TenantContext.personal('u1')
        billing = resolve_billing_user(tenant, 'u1', needs_receipt=False, source_message_id='m1')
        self.assertEqual(billing.billing_line_user_id, 'u1')
        self.assertFalse(billing.pooled)

    @patch('services.usage_limiter.random.choice', return_value='donor-b')
    @patch('services.usage_limiter.list_eligible_donors', return_value=['donor-b'])
    @patch('services.usage_limiter.has_quota_headroom', side_effect=[False, True])
    def test_resolve_billing_user_pool(self, _headroom, _donors, _choice):
        tenant = TenantContext.group('g1', 'u1')
        billing = resolve_billing_user(tenant, 'u1', needs_receipt=False, source_message_id='m1')
        self.assertEqual(billing.billing_line_user_id, 'donor-b')
        self.assertTrue(billing.pooled)

    @patch('services.usage_limiter.is_usage_tracking_enabled', return_value=False)
    def test_prepare_skips_when_disabled(self, _enabled):
        tenant = TenantContext.personal('u1')
        result = prepare_inbound_usage(tenant, 'u1', 'm1', text='Lunch 1200')
        self.assertTrue(result.allowed)
        self.assertIsInstance(result.billing_context, UsageBillingContext)

    @patch('services.usage_limiter.check_sender_rate_limits', return_value=LimitDenyReason.RATE_MINUTE)
    @patch('services.usage_limiter.is_usage_tracking_enabled', return_value=True)
    @patch('services.usage_limiter.upsert_tenant_chat_member')
    def test_prepare_blocks_rate_limit(self, _upsert, _enabled, _rate):
        tenant = TenantContext.personal('u1')
        result = prepare_inbound_usage(tenant, 'u1', 'm1', text='Lunch 1200')
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, LimitDenyReason.RATE_MINUTE)


if __name__ == '__main__':
    unittest.main()
