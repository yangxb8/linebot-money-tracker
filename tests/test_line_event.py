import unittest
from unittest.mock import patch

from services.line_event import extract_text_message


class TestLineEventExtraction(unittest.TestCase):
    def test_extract_text_message_returns_text_for_supported_event(self):
        class DummyTextMessage:
            def __init__(self, text):
                self.text = text

        class DummyMessageEvent:
            def __init__(self, message):
                self.message = message

        event = DummyMessageEvent(DummyTextMessage('Hello LINE'))
        self.assertEqual(extract_text_message(event), 'Hello LINE')

    def test_extract_text_message_returns_none_for_non_text_event(self):
        class DummyMessageEvent:
            def __init__(self, message):
                self.message = message

        class DummyNonTextMessage:
            pass

        event = DummyMessageEvent(DummyNonTextMessage())
        self.assertIsNone(extract_text_message(event))

    def test_extract_text_message_returns_none_for_empty_text(self):
        class DummyTextMessage:
            def __init__(self, text):
                self.text = text

        class DummyMessageEvent:
            def __init__(self, message):
                self.message = message

        event = DummyMessageEvent(DummyTextMessage('   '))
        self.assertIsNone(extract_text_message(event))


if __name__ == '__main__':
    unittest.main()
