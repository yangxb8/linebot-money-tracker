import unittest

from services.message_retry import is_retry_intent


class TestMessageRetryIntent(unittest.TestCase):
    def test_accepts_strict_retry_phrases(self):
        for phrase in ('retry', 'Retry', 'try again', 'again', 'もう一度', '再試行', '重试', '再试'):
            with self.subTest(phrase=phrase):
                self.assertTrue(is_retry_intent(phrase))

    def test_rejects_non_retry_phrases(self):
        for phrase in ('yes', 'ok', 'はい', 'ランチ 1200円', '3800円', 'retry please'):
            with self.subTest(phrase=phrase):
                self.assertFalse(is_retry_intent(phrase))


if __name__ == '__main__':
    unittest.main()
