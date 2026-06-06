from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


@dataclass(frozen=True)
class MessageContext:
    """LINE user and message identifiers for expense idempotency."""

    line_user_id: str
    source_message_id: str


@dataclass(frozen=True)
class ReplyContext:
    """Inbound reply-to-confirmation context."""

    line_user_id: str
    user_reply_message_id: str
    quoted_bot_message_id: str


@dataclass(frozen=True)
class ConfirmationItemSnapshot:
    line_item_index: int
    expense_id: str
    description: str
    amount: Decimal
    currency: str
    category_guess_code: str
    category_alternatives: tuple[str, ...]


@dataclass(frozen=True)
class ConfirmationSavePayload:
    line_user_id: str
    confirmation_text: str
    items: tuple[ConfirmationItemSnapshot, ...]


@dataclass(frozen=True)
class BotReply:
    text: str
    confirmation: Optional[ConfirmationSavePayload] = None
