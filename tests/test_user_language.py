import unittest

from services.user_language import (
    parse_explicit_language_request,
    resolve_reply_language,
    SOURCE_USER_REQUEST,
)


class TestUserLanguage(unittest.TestCase):
    def test_parse_explicit_english(self):
        self.assertEqual(parse_explicit_language_request('please reply in English'), 'en')

    def test_parse_explicit_japanese(self):
        self.assertEqual(parse_explicit_language_request('日本語で返信してください'), 'ja')

    def test_resolve_defaults_to_ja_without_user(self):
        self.assertEqual(resolve_reply_language(None, None), 'ja')
