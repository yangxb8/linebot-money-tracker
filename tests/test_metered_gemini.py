import unittest
from unittest.mock import MagicMock, patch

from services.usage_metering import UsageBillingContext, usage_billing_scope
from services.metered_gemini import MeteredGeminiClient


class TestMeteredGemini(unittest.IsolatedAsyncioTestCase):
    async def test_records_one_event_on_success(self):
        client = MeteredGeminiClient(api_key='test-key')
        billing = UsageBillingContext(
            billing_line_user_id='u1',
            sender_line_user_id='u1',
            source_message_id='msg-1',
            tenant_type='user',
            tenant_id='u1',
            pooled=False,
        )

        with usage_billing_scope(billing):
            with patch.object(client, '_generate_content_with_retry', return_value='{"is_expense": true}') as gen_mock:
                with patch('services.metered_gemini.is_usage_tracking_enabled', return_value=True):
                    with patch('services.metered_gemini.check_billing_headroom_for_operation', return_value=None):
                        with patch('services.metered_gemini.record_llm_backed_message', return_value=True) as window_mock:
                            with patch('services.metered_gemini.record_llm_usage', return_value=True) as record_mock:
                                with patch('services.usage_metering.llm_operation_scope') as scope_mock:
                                    scope_mock.return_value.__enter__ = MagicMock(return_value=None)
                                    scope_mock.return_value.__exit__ = MagicMock(return_value=False)
                                    result = await client.generate_reply('hello')

        self.assertIn('is_expense', result)
        gen_mock.assert_awaited_once()
        window_mock.assert_called_once()
        record_mock.assert_called_once()
        self.assertEqual(record_mock.call_args.kwargs['operation_label'], 'text')


if __name__ == '__main__':
    unittest.main()
