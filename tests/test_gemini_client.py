import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault('GEMINI_API_KEY', 'test_key')

from google.genai.errors import ClientError, ServerError

from services.gemini_client import (
    GEMINI_3_FLASH_MODEL,
    GEMINI_GENERAL_MODEL_FALLBACK_CHAIN,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_RECEIPT_IMAGE_MODEL_FALLBACK_CHAIN,
    GeminiClient,
    GeminiUsageLimitError,
)


def _server_error_503() -> ServerError:
    return ServerError(
        503,
        {'error': {'code': 503, 'message': 'high demand', 'status': 'UNAVAILABLE'}},
    )


def _quota_error_429() -> ClientError:
    return ClientError(
        429,
        {'error': {'code': 429, 'message': 'quota exceeded', 'status': 'RESOURCE_EXHAUSTED'}},
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
            self.assertEqual(kwargs['model'], GEMINI_MODEL)

    async def test_generate_reply_returns_text(self):
        fake_response = MagicMock()
        fake_response.text = 'Hello from Gemini'

        client = GeminiClient(api_key='test_key')
        with patch.object(
            client.client.models,
            'generate_content',
            return_value=fake_response,
        ) as generate_content:
            result = await client.generate_reply('Hello world')
            self.assertEqual(result, 'Hello from Gemini')
            self.assertEqual(generate_content.call_args.kwargs['model'], GEMINI_MODEL)

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
            return_value=fake_response,
        ):
            with self.assertRaises(RuntimeError):
                await client.generate_reply('Hello world')

    async def test_generate_reply_handles_api_errors(self):
        client = GeminiClient(api_key='test_key')
        with patch.object(
            client.client.models,
            'generate_content',
            side_effect=Exception('API error'),
        ):
            with self.assertRaises(RuntimeError):
                await client.generate_reply('Hello world')

    async def test_generate_json_reply_with_image_starts_at_35_flash(self):
        fake_response = MagicMock()
        fake_response.text = '{"items":[],"total":0,"currency":"JPY"}'

        client = GeminiClient(api_key='test_key')
        with patch.object(
            client.client.models,
            'generate_content',
            return_value=fake_response,
        ) as generate_content:
            result = await client.generate_json_reply_with_image(
                'Parse receipt',
                b'fake-image',
                'image/jpeg',
            )
            self.assertIn('items', result)
            _, kwargs = generate_content.call_args
            self.assertEqual(kwargs['model'], GEMINI_MODEL)
            self.assertEqual(kwargs['model'], GEMINI_GENERAL_MODEL_FALLBACK_CHAIN[0])

    async def test_generate_reply_with_image_uses_default_model_chain(self):
        fake_response = MagicMock()
        fake_response.text = '{"is_expense": true}'

        client = GeminiClient(api_key='test_key')
        with patch.object(
            client.client.models,
            'generate_content',
            return_value=fake_response,
        ) as generate_content:
            result = await client.generate_reply_with_image(
                'Classify this image',
                b'fake-image',
                'image/jpeg',
            )
            self.assertEqual(result, '{"is_expense": true}')
            self.assertEqual(generate_content.call_args.kwargs['model'], GEMINI_MODEL)

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

    async def test_general_fallback_chain_includes_3_flash_before_25_flash(self):
        flash_index = GEMINI_GENERAL_MODEL_FALLBACK_CHAIN.index(GEMINI_3_FLASH_MODEL)
        flash_25_index = GEMINI_GENERAL_MODEL_FALLBACK_CHAIN.index('gemini-2.5-flash')
        self.assertLess(flash_index, flash_25_index)

    async def test_generate_reply_falls_back_on_quota(self):
        fake_response = MagicMock()
        fake_response.text = 'Fallback response'
        client = GeminiClient(api_key='test_key')

        with patch.object(
            client.client.models,
            'generate_content',
            side_effect=[_quota_error_429(), fake_response],
        ) as generate_mock:
            result = await client.generate_reply('Hello world')

        self.assertEqual(result, 'Fallback response')
        self.assertEqual(generate_mock.call_count, 2)
        first_model = generate_mock.call_args_list[0].kwargs['model']
        second_model = generate_mock.call_args_list[1].kwargs['model']
        self.assertEqual(first_model, GEMINI_GENERAL_MODEL_FALLBACK_CHAIN[0])
        self.assertEqual(second_model, GEMINI_GENERAL_MODEL_FALLBACK_CHAIN[1])
        self.assertEqual(second_model, GEMINI_3_FLASH_MODEL)

    async def test_generate_reply_raises_usage_limit_when_all_models_quota(self):
        client = GeminiClient(api_key='test_key')
        quota_calls = len(GEMINI_GENERAL_MODEL_FALLBACK_CHAIN)

        with patch.object(
            client.client.models,
            'generate_content',
            side_effect=[_quota_error_429()] * quota_calls,
        ) as generate_mock:
            with self.assertRaises(GeminiUsageLimitError):
                await client.generate_reply('Hello world')

        self.assertEqual(generate_mock.call_count, quota_calls)

    async def test_receipt_image_falls_back_on_quota_like_general_chain(self):
        fake_response = MagicMock()
        fake_response.text = '{"items":[],"total":0,"currency":"JPY"}'
        client = GeminiClient(api_key='test_key')

        with patch.object(
            client.client.models,
            'generate_content',
            side_effect=[_quota_error_429(), fake_response],
        ) as generate_mock:
            result = await client.generate_json_reply_with_image(
                'Parse receipt',
                b'fake-image',
                'image/jpeg',
            )

        self.assertIn('items', result)
        self.assertEqual(generate_mock.call_count, 2)
        self.assertEqual(
            generate_mock.call_args_list[0].kwargs['model'],
            GEMINI_GENERAL_MODEL_FALLBACK_CHAIN[0],
        )
        self.assertEqual(
            generate_mock.call_args_list[1].kwargs['model'],
            GEMINI_3_FLASH_MODEL,
        )
        config = generate_mock.call_args_list[1].kwargs['config']
        self.assertEqual(config.response_mime_type, 'application/json')
        self.assertEqual(config.max_output_tokens, 8192)
        self.assertTrue(config.automatic_function_calling.disable)

    async def test_receipt_image_raises_usage_limit_when_full_chain_quota(self):
        client = GeminiClient(api_key='test_key')
        quota_calls = len(GEMINI_GENERAL_MODEL_FALLBACK_CHAIN)

        with patch.object(
            client.client.models,
            'generate_content',
            side_effect=[_quota_error_429()] * quota_calls,
        ) as generate_mock:
            with self.assertRaises(GeminiUsageLimitError):
                await client.generate_json_reply_with_image(
                    'Parse receipt',
                    b'fake-image',
                    'image/jpeg',
                )

        self.assertEqual(generate_mock.call_count, quota_calls)


if __name__ == '__main__':
    unittest.main()
