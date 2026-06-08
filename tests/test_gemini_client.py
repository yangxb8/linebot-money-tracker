import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault('GEMINI_API_KEY', 'test_key')

from google.genai.errors import ServerError

from services.gemini_client import GEMINI_MAX_RETRIES, GeminiClient


def _server_error_503() -> ServerError:
    return ServerError(
        503,
        {'error': {'code': 503, 'message': 'high demand', 'status': 'UNAVAILABLE'}},
    )


class TestGeminiClient(unittest.IsolatedAsyncioTestCase):
    async def test_generate_json_reply_returns_text(self):
        fake_response = MagicMock()
        fake_response.text = '{"action":"update"}'

        client = GeminiClient(api_key='test_key')
        with patch.object(
            client.client.models,
            'generate_content',
            return_value=fake_response,
        ) as generate_content:
            result = await client.generate_json_reply('Return JSON')
            self.assertEqual(result, '{"action":"update"}')
            _, kwargs = generate_content.call_args
            self.assertEqual(kwargs['config'].response_mime_type, 'application/json')

    async def test_generate_reply_returns_text(self):
        fake_response = MagicMock()
        fake_response.text = 'Hello from Gemini'

        client = GeminiClient(api_key='test_key')
        with patch.object(
            client.client.models,
            'generate_content',
            return_value=fake_response
        ):
            result = await client.generate_reply('Hello world')
            self.assertEqual(result, 'Hello from Gemini')

    async def test_generate_reply_raises_for_empty_prompt(self):
        client = GeminiClient(api_key='test_key')
        with self.assertRaises(ValueError):
            await client.generate_reply('')

    async def test_generate_reply_raises_for_empty_response(self):
        fake_response = MagicMock()
        fake_response.text = ''

        client = GeminiClient(api_key='test_key')
        with patch.object(
            client.client.models,
            'generate_content',
            return_value=fake_response
        ):
            with self.assertRaises(RuntimeError):
                await client.generate_reply('Hello world')

    async def test_generate_reply_handles_api_errors(self):
        client = GeminiClient(api_key='test_key')
        with patch.object(
            client.client.models,
            'generate_content',
            side_effect=Exception('API error')
        ):
            with self.assertRaises(RuntimeError):
                await client.generate_reply('Hello world')

    async def test_generate_reply_with_image_returns_text(self):
        fake_response = MagicMock()
        fake_response.text = '{"is_expense": true}'

        client = GeminiClient(api_key='test_key')
        with patch.object(
            client.client.models,
            'generate_content',
            return_value=fake_response
        ):
            result = await client.generate_reply_with_image(
                'Classify this image',
                b'fake-image',
                'image/jpeg',
            )
            self.assertEqual(result, '{"is_expense": true}')

    async def test_generate_reply_retries_on_503_then_succeeds(self):
        fake_response = MagicMock()
        fake_response.text = 'Recovered response'
        client = GeminiClient(api_key='test_key')

        with patch.object(
            client.client.models,
            'generate_content',
            side_effect=[_server_error_503(), fake_response],
        ) as generate_mock, patch('services.gemini_client.asyncio.sleep', AsyncMock()) as sleep_mock:
            result = await client.generate_reply('Hello world')

        self.assertEqual(result, 'Recovered response')
        self.assertEqual(generate_mock.call_count, 2)
        sleep_mock.assert_awaited_once()

    async def test_generate_reply_stops_after_max_retries_on_503(self):
        client = GeminiClient(api_key='test_key')
        max_attempts = GEMINI_MAX_RETRIES + 1

        with patch.object(
            client.client.models,
            'generate_content',
            side_effect=[_server_error_503()] * max_attempts,
        ) as generate_mock, patch('services.gemini_client.asyncio.sleep', AsyncMock()) as sleep_mock:
            with self.assertRaises(RuntimeError):
                await client.generate_reply('Hello world')

        self.assertEqual(generate_mock.call_count, max_attempts)
        self.assertEqual(sleep_mock.await_count, GEMINI_MAX_RETRIES)

    async def test_generate_reply_does_not_retry_non_retryable_errors(self):
        client = GeminiClient(api_key='test_key')

        with patch.object(
            client.client.models,
            'generate_content',
            side_effect=ValueError('bad request'),
        ) as generate_mock, patch('services.gemini_client.asyncio.sleep', AsyncMock()) as sleep_mock:
            with self.assertRaises(RuntimeError):
                await client.generate_reply('Hello world')

        self.assertEqual(generate_mock.call_count, 1)
        sleep_mock.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
