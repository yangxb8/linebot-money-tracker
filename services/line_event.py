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
