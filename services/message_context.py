from dataclasses import dataclass


@dataclass(frozen=True)
class MessageContext:
    """LINE user and message identifiers for expense idempotency."""

    line_user_id: str
    source_message_id: str
