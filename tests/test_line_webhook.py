import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

# Provide test environment values before importing the app.
os.environ.setdefault('LINE_CHANNEL_SECRET', 'test_secret')
os.environ.setdefault('LINE_CHANNEL_ACCESS_TOKEN', 'test_token')
os.environ.setdefault('GEMINI_API_KEY', 'test_gemini_key')
os.environ.setdefault('GEMINI_API_URL', 'https://example.com/gemini')

from main import handle_callback


class DummyTextMessage:
    def __init__(self, text):
        self.text = text


class DummyMessageEvent:
    def __init__(self, message):
        self.message = message
        self.reply_token = 'reply-token'


class DummyRequest:
    def __init__(self, body, headers=None):
        self._body = body.encode('utf-8')
        self.headers = headers or {'X-Line-Signature': 'signature'}

    async def body(self):
        return self._body


class TestLineWebhook(unittest.IsolatedAsyncioTestCase):
    async def test_handle_callback_replies_for_text_message(self):
        request = DummyRequest('{"events": []}')
        event = DummyMessageEvent(DummyTextMessage('Hello bot'))

        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()

        with patch('main.parser.parse', parse_mock), patch('main.gemini_client.generate_reply', AsyncMock(return_value='Hello from Gemini')), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.MessageEvent', DummyMessageEvent):
            response = await handle_callback(request)

        reply_mock.assert_awaited_once()
        self.assertEqual(response, 'OK')

    async def test_handle_callback_returns_fallback_for_unsupported_event(self):
        class DummyNonTextMessage:
            def __init__(self):
                self.text = None

        event = DummyMessageEvent(DummyNonTextMessage())
        request = DummyRequest('{"events": []}')
        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()

        with patch('main.parser.parse', parse_mock), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.MessageEvent', DummyMessageEvent):
            response = await handle_callback(request)

        reply_mock.assert_awaited_once()
        self.assertEqual(response, 'OK')

    async def test_handle_callback_logs_gemini_reply_generation(self):
        request = DummyRequest('{"events": []}')
        event = DummyMessageEvent(DummyTextMessage('Hello bot'))

        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()

        with patch('main.parser.parse', parse_mock), patch('main.gemini_client.generate_reply', AsyncMock(return_value='Hello from Gemini')), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.logger.info') as logger_info, patch('main.MessageEvent', DummyMessageEvent):
            response = await handle_callback(request)

        logger_info.assert_any_call('Gemini reply generated successfully')
        reply_mock.assert_awaited_once()
        self.assertEqual(response, 'OK')

    async def test_handle_callback_returns_error_message_when_gemini_fails(self):
        request = DummyRequest('{"events": []}')
        event = DummyMessageEvent(DummyTextMessage('Hello bot'))

        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()

        with patch('main.parser.parse', parse_mock), patch('main.gemini_client.generate_reply', AsyncMock(side_effect=RuntimeError('Gemini unavailable'))), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.MessageEvent', DummyMessageEvent):
            response = await handle_callback(request)

        reply_mock.assert_awaited_once()
        call_args = reply_mock.call_args[0]
        message_text = call_args[0].messages[0].text
        self.assertIn('Sorry, I couldn\'t generate a response right now', message_text)
        self.assertEqual(response, 'OK')


if __name__ == '__main__':
    unittest.main()
