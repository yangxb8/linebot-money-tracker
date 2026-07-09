import os
import unittest
from unittest.mock import patch

from services.webapp_intent import (
    dashboard_url,
    is_webapp_request_obvious,
    webapp_link_reply,
)


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


class TestWebappLinkReply(unittest.TestCase):
    def test_includes_configured_url(self):
        with patch.dict(os.environ, {'DASHBOARD_LIFF_URL': 'https://liff.line.me/abc123'}):
            reply = webapp_link_reply('en')
        self.assertIn('https://liff.line.me/abc123', reply)

    def test_unavailable_without_url(self):
        with patch.dict(os.environ, {}, clear=True):
            reply = webapp_link_reply('en')
        self.assertIn('available', reply.lower())

    def test_dashboard_url_reads_env(self):
        with patch.dict(os.environ, {'DASHBOARD_LIFF_URL': 'https://liff.line.me/test'}):
            self.assertEqual(dashboard_url(), 'https://liff.line.me/test')


if __name__ == '__main__':
    unittest.main()
