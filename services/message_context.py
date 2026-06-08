from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from services.tenant_context import TenantContext


@dataclass(frozen=True)
class MessageContext:
    """LINE user and message identifiers for expense idempotency."""

    tenant: TenantContext
    source_message_id: str

    @property
    def line_user_id(self) -> str:
        return self.tenant.logged_by_line_user_id


@dataclass(frozen=True)
class ReplyContext:
    """Inbound reply-to-confirmation context."""

    tenant: TenantContext
    user_reply_message_id: str
    quoted_bot_message_id: str

    @property
    def line_user_id(self) -> str:
        return self.tenant.logged_by_line_user_id


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
    tenant: TenantContext
    confirmation_text: str
    items: tuple[ConfirmationItemSnapshot, ...]

    @property
    def line_user_id(self) -> str:
        return self.tenant.logged_by_line_user_id


@dataclass(frozen=True)
class BotReply:
    text: str
    confirmation: Optional[ConfirmationSavePayload] = None
