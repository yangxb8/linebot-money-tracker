import unittest
from unittest.mock import patch

from services.line_event import (
    extract_group_id,
    extract_quoted_message_id,
    extract_room_id,
    extract_source_type,
    extract_text_message,
)


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

    def test_extract_quoted_message_id(self):
        class DummyMessage:
            def __init__(self):
                self.quoted_message_id = 'bot-msg-123'

        class DummyEvent:
            def __init__(self):
                self.message = DummyMessage()

        self.assertEqual(extract_quoted_message_id(DummyEvent()), 'bot-msg-123')

    def test_extract_source_type_group(self):
        class DummySource:
            type = 'group'

        class DummyEvent:
            source = DummySource()

        self.assertEqual(extract_source_type(DummyEvent()), 'group')

    def test_extract_group_id(self):
        class DummySource:
            groupId = 'group-abc'

        class DummyEvent:
            source = DummySource()

        self.assertEqual(extract_group_id(DummyEvent()), 'group-abc')

    def test_extract_room_id(self):
        class DummySource:
            room_id = 'room-xyz'

        class DummyEvent:
            source = DummySource()

        self.assertEqual(extract_room_id(DummyEvent()), 'room-xyz')

    def test_extract_quoted_message_id_camel_case(self):
        class DummyMessage:
            def __init__(self):
                self.quotedMessageId = 'bot-msg-456'

        class DummyEvent:
            def __init__(self):
                self.message = DummyMessage()

        self.assertEqual(extract_quoted_message_id(DummyEvent()), 'bot-msg-456')


if __name__ == '__main__':
    unittest.main()
