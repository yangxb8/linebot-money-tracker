from typing import Optional


def extract_text_message(event) -> Optional[str]:
    """Return trimmed text content for supported LINE text message events."""
    message = getattr(event, "message", None)
    if message is None:
        return None

    text = getattr(message, "text", None)
    if not isinstance(text, str):
        return None

    return text.strip() or None


def extract_line_user_id(event) -> Optional[str]:
    """Return LINE user ID from a message event source."""
    source = getattr(event, 'source', None)
    if source is None:
        return None

    user_id = getattr(source, 'user_id', None)
    if not isinstance(user_id, str):
        return None

    return user_id.strip() or None


def extract_source_message_id(event) -> Optional[str]:
    """Return LINE message ID used for expense idempotency."""
    message = getattr(event, 'message', None)
    if message is None:
        return None

    message_id = getattr(message, 'id', None)
    if not isinstance(message_id, str):
        return None

    return message_id.strip() or None


def extract_quoted_message_id(event) -> Optional[str]:
    """Return quoted bot message ID when user replies to a specific message."""
    message = getattr(event, 'message', None)
    if message is None:
        return None

    quoted_id = getattr(message, 'quoted_message_id', None)
    if quoted_id is None:
        quoted_id = getattr(message, 'quotedMessageId', None)
    if not isinstance(quoted_id, str):
        return None

    return quoted_id.strip() or None


def extract_image_message_id(event) -> Optional[str]:
    """Return the image message ID for supported LINE image events."""
    message = getattr(event, "message", None)
    if message is None:
        return None

    if getattr(message, "type", "").lower() != "image":
        return None

    image_id = getattr(message, "id", None)
    if not isinstance(image_id, str):
        return None

    return image_id.strip() or None
