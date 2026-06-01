from typing import Optional


def extract_text_message(event) -> Optional[str]:
    """Return trimmed text content for supported LINE message events."""
    message = getattr(event, "message", None)
    if message is None:
        return None

    text = getattr(message, "text", None)
    if not isinstance(text, str):
        return None

    return text.strip() or None
