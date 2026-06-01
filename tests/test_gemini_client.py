import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from services.gemini_client import GeminiClient


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception('Status error')

    def json(self):
        return self._json_data


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, headers):
        return FakeResponse({'text': 'Hello from Gemini'})


class TestGeminiClient(unittest.IsolatedAsyncioTestCase):
    async def test_generate_reply_returns_text(self):
        client = GeminiClient(api_key='key', api_url='https://example.com/gemini')

        with patch('services.gemini_client.httpx.AsyncClient', FakeAsyncClient):
            result = await client.generate_reply('Hello world')
            self.assertEqual(result, 'Hello from Gemini')

    async def test_generate_reply_raises_for_empty_prompt(self):
        client = GeminiClient(api_key='key', api_url='https://example.com/gemini')
        with self.assertRaises(ValueError):
            await client.generate_reply('')

    async def test_generate_reply_raises_with_missing_config(self):
        client = GeminiClient(api_key=None, api_url=None)
        with self.assertRaises(RuntimeError):
            await client.generate_reply('Hello world')


if __name__ == '__main__':
    unittest.main()
