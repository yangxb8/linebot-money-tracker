import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('GEMINI_API_KEY', 'test_key')

from services.gemini_client import GeminiClient


class TestGeminiClient(unittest.IsolatedAsyncioTestCase):
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


if __name__ == '__main__':
    unittest.main()
