import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.webapp_intent import (
    _parse_webapp_intent_response,
    dashboard_url,
    is_webapp_intent_text,
    is_webapp_request_obvious,
    webapp_link_reply,
)


class TestParseWebappIntentResponse(unittest.TestCase):
    def test_parses_json_true(self):
        self.assertTrue(_parse_webapp_intent_response('{"is_webapp_request": true}'))

    def test_parses_json_false(self):
        self.assertFalse(_parse_webapp_intent_response('{"is_webapp_request": false}'))

    def test_rejects_invalid_json(self):
        self.assertFalse(_parse_webapp_intent_response('not json'))


class TestWebappRequestObvious(unittest.TestCase):
    def test_matches_dashboard(self):
        self.assertTrue(is_webapp_request_obvious('dashboard'))

    def test_matches_japanese(self):
        self.assertTrue(is_webapp_request_obvious('家計簿'))

    def test_rejects_expense_text(self):
        self.assertFalse(is_webapp_request_obvious('Lunch 1200 yen'))

    def test_rejects_empty(self):
        self.assertFalse(is_webapp_request_obvious(''))
        self.assertFalse(is_webapp_request_obvious(None))


class TestWebappIntentAsync(unittest.IsolatedAsyncioTestCase):
    async def test_shortcut_skips_gemini(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock()

        result = await is_webapp_intent_text('open dashboard', gemini)
        self.assertTrue(result)
        gemini.generate_reply.assert_not_awaited()

    async def test_llm_path_calls_gemini(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(return_value='{"is_webapp_request": true}')

        result = await is_webapp_intent_text('how can I see my expenses online?', gemini)
        self.assertTrue(result)
        gemini.generate_reply.assert_awaited_once()

    async def test_llm_rejects_non_webapp(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(return_value='{"is_webapp_request": false}')

        result = await is_webapp_intent_text('what is the weather?', gemini)
        self.assertFalse(result)


class TestWebappLinkReply(unittest.TestCase):
    def test_includes_configured_url(self):
        with patch.dict(os.environ, {'DASHBOARD_LIFF_URL': 'https://liff.line.me/abc123'}):
            reply = webapp_link_reply('en')
        self.assertIn('https://liff.line.me/abc123', reply)

    def test_unavailable_without_url(self):
        with patch.dict(os.environ, {}, clear=True):
            reply = webapp_link_reply('en')
        self.assertIn('not available', reply.lower())

    def test_dashboard_url_reads_env(self):
        with patch.dict(os.environ, {'DASHBOARD_LIFF_URL': 'https://liff.line.me/test'}):
            self.assertEqual(dashboard_url(), 'https://liff.line.me/test')


if __name__ == '__main__':
    unittest.main()
