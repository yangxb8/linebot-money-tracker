import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

# Provide test environment values before importing the app.
os.environ.setdefault('LINE_CHANNEL_SECRET', 'test_secret')
os.environ.setdefault('LINE_CHANNEL_ACCESS_TOKEN', 'test_token')
os.environ.setdefault('GEMINI_API_KEY', 'test_gemini_key')

import main
from main import handle_callback, WEBHOOK_REQUIRED_VARS
from services.message_handler import CANNED_UNSUPPORTED_REPLY, ERROR_REPLY_TEXT


class DummyTextMessage:
    def __init__(self, text):
        self.text = text


class DummyImageMessage:
    def __init__(self, message_id):
        self.type = 'image'
        self.id = message_id


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
    def test_module_initializes_with_webhook_env(self):
        self.assertIsNotNone(main.parser)
        self.assertIsNotNone(main.gemini_client)
        self.assertEqual(len(WEBHOOK_REQUIRED_VARS), 3)

    async def test_handle_callback_replies_for_text_message(self):
        request = DummyRequest('{"events": []}')
        event = DummyMessageEvent(DummyTextMessage('Hello bot'))

        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()

        with patch('main.parser.parse', parse_mock), patch(
            'main.process_text_message', AsyncMock(return_value=CANNED_UNSUPPORTED_REPLY)
        ), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.MessageEvent', DummyMessageEvent):
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

    async def test_handle_callback_processes_text_via_handler(self):
        request = DummyRequest('{"events": []}')
        event = DummyMessageEvent(DummyTextMessage('Lunch 120 THB at cafe'))

        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()

        with patch('main.parser.parse', parse_mock), patch(
            'main.process_text_message', AsyncMock(return_value='Hello from handler')
        ), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.MessageEvent', DummyMessageEvent):
            response = await handle_callback(request)

        reply_mock.assert_awaited_once()
        message_text = reply_mock.call_args[0][0].messages[0].text
        self.assertEqual(message_text, 'Hello from handler')
        self.assertEqual(response, 'OK')

    async def test_handle_callback_returns_error_message_from_handler(self):
        request = DummyRequest('{"events": []}')
        event = DummyMessageEvent(DummyTextMessage('Lunch 120 THB at cafe'))

        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()

        with patch('main.parser.parse', parse_mock), patch(
            'main.process_text_message', AsyncMock(return_value=ERROR_REPLY_TEXT)
        ), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.MessageEvent', DummyMessageEvent):
            response = await handle_callback(request)

        message_text = reply_mock.call_args[0][0].messages[0].text
        self.assertIn('Sorry, I couldn\'t generate a response right now', message_text)
        self.assertEqual(response, 'OK')

    async def test_handle_callback_rejects_non_expense_text(self):
        request = DummyRequest('{"events": []}')
        event = DummyMessageEvent(DummyTextMessage('Hello bot'))

        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()

        with patch('main.parser.parse', parse_mock), patch(
            'main.process_text_message', AsyncMock(return_value=CANNED_UNSUPPORTED_REPLY)
        ), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.MessageEvent', DummyMessageEvent):
            response = await handle_callback(request)

        reply_mock.assert_awaited_once()
        message_text = reply_mock.call_args[0][0].messages[0].text
        self.assertIn('only accept expense submissions', message_text)
        self.assertEqual(response, 'OK')

    async def test_handle_callback_processes_image_message(self):
        request = DummyRequest('{"events": []}')
        event = DummyMessageEvent(DummyImageMessage('image-id'))

        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()
        blob_instance = Mock()
        blob_instance.get_message_content.return_value = b'fake-image-bytes'

        with patch('main.parser.parse', parse_mock), patch('main.AsyncMessagingApiBlob', Mock(return_value=blob_instance)), patch(
            'main.process_image_message',
            AsyncMock(return_value='Detected expense(s):\n- Lunch: 120.0 THB'),
        ), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.MessageEvent', DummyMessageEvent):
            main.async_api_client = Mock()
            response = await handle_callback(request)

        reply_mock.assert_awaited_once()
        message_text = reply_mock.call_args[0][0].messages[0].text
        self.assertIn('Detected expense(s):', message_text)
        self.assertEqual(response, 'OK')

    async def test_handle_callback_rejects_non_receipt_image(self):
        request = DummyRequest('{"events": []}')
        event = DummyMessageEvent(DummyImageMessage('image-id'))

        parse_mock = Mock(return_value=[event])
        reply_mock = AsyncMock()
        blob_instance = Mock()
        blob_instance.get_message_content.return_value = b'cat-photo-bytes'

        with patch('main.parser.parse', parse_mock), patch('main.AsyncMessagingApiBlob', Mock(return_value=blob_instance)), patch(
            'main.process_image_message', AsyncMock(return_value=CANNED_UNSUPPORTED_REPLY)
        ), patch('main.line_bot_api', Mock(reply_message=reply_mock)), patch('main.MessageEvent', DummyMessageEvent):
            main.async_api_client = Mock()
            response = await handle_callback(request)

        reply_mock.assert_awaited_once()
        message_text = reply_mock.call_args[0][0].messages[0].text
        self.assertIn('only accept expense submissions', message_text)
        self.assertEqual(response, 'OK')


if __name__ == '__main__':
    unittest.main()
