import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.gemini_client import GeminiClient
from services.message_context import RetryContext
from services.message_retry import process_message_retry, retry_expired_reply, retry_not_found_reply
from services.tenant_context import TenantContext


class TestProcessMessageRetry(unittest.IsolatedAsyncioTestCase):
    async def test_returns_not_found_when_anchor_missing(self):
        gemini = MagicMock(spec=GeminiClient)
        ctx = RetryContext(
            tenant=TenantContext.personal('u1'),
            retry_reply_message_id='retry-1',
            bot_error_message_id='missing-bot',
            reply_language='en',
        )
        with patch('services.message_retry.get_failure_retry_anchor', return_value=None):
            result = await process_message_retry(ctx, gemini, AsyncMock())
        self.assertEqual(result.text, retry_not_found_reply('en'))

    async def test_retries_stored_text_for_original_sender(self):
        gemini = MagicMock(spec=GeminiClient)
        ctx = RetryContext(
            tenant=TenantContext.group('g1', 'u2'),
            retry_reply_message_id='retry-1',
            bot_error_message_id='bot-error-1',
            reply_language='en',
        )
        anchor = MagicMock(
            bot_error_message_id='bot-error-1',
            original_message_id='msg-1',
            original_line_user_id='u1',
            tenant_type='group',
            tenant_id='g1',
            failure_kind='processing_error',
        )
        inbound = MagicMock(
            message_id='msg-1',
            line_user_id='u1',
            tenant_type='group',
            tenant_id='g1',
            message_type='text',
            text_content='Lunch 1200',
            created_at=MagicMock(),
        )
        with patch('services.message_retry.get_failure_retry_anchor', return_value=anchor), patch(
            'services.message_retry.get_inbound_message',
            return_value=inbound,
        ), patch(
            'services.message_retry.process_text_message',
            AsyncMock(return_value=MagicMock(text='ok', confirmation=None, retryable_failure=None)),
        ) as process_text:
            result = await process_message_retry(ctx, gemini, AsyncMock())

        self.assertEqual(result.text, 'ok')
        message_context = process_text.await_args.args[2]
        self.assertEqual(message_context.source_message_id, 'msg-1')
        self.assertEqual(message_context.tenant.logged_by_line_user_id, 'u1')

    async def test_returns_expired_when_inbound_missing(self):
        gemini = MagicMock(spec=GeminiClient)
        ctx = RetryContext(
            tenant=TenantContext.personal('u1'),
            retry_reply_message_id='retry-1',
            bot_error_message_id='bot-error-1',
            reply_language='en',
        )
        anchor = MagicMock(
            bot_error_message_id='bot-error-1',
            original_message_id='msg-1',
            original_line_user_id='u1',
            tenant_type='user',
            tenant_id='u1',
            failure_kind='processing_error',
        )
        with patch('services.message_retry.get_failure_retry_anchor', return_value=anchor), patch(
            'services.message_retry.get_inbound_message',
            return_value=None,
        ):
            result = await process_message_retry(ctx, gemini, AsyncMock())
        self.assertEqual(result.text, retry_expired_reply('en'))


if __name__ == '__main__':
    unittest.main()
