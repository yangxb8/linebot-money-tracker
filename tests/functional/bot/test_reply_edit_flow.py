"""Scenario: bot.expense.reply_edit."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from services.confirmation_repository import ConfirmationRecord
from services.message_context import ReplyEditResult
from services.tenant_context import TenantContext
from tests.functional.bot.conftest import assert_callback_ok, post_signed
from tests.functional.bot.helpers.webhook_events import text_message_event, webhook_body


def _expense_confirmation() -> ConfirmationRecord:
    return ConfirmationRecord(
        id="conf-expense-1",
        bot_message_id="bot-msg-1",
        tenant=TenantContext.personal("U4af4980629"),
        confirmation_text="Logged Lunch",
        items_snapshot=(
            {
                "line_item_index": 0,
                "expense_id": "exp-1",
                "description": "Lunch",
                "amount": float(Decimal("1200")),
                "currency": "JPY",
                "category_guess_code": "unknown",
                "category_alternatives": [],
            },
        ),
        pending_action=None,
        pending_payload=None,
    )


@pytest.mark.functional
def test_bot_expense_reply_edit(client, reply_mock):
    """Reply-to confirmation with new amount → edit applied; reply reflects change."""
    body = webhook_body(
        text_message_event(
            "3800円",
            message_id="msg-edit-1",
            quoted_message_id="bot-msg-1",
        )
    )

    with patch("main.save_inbound_text_message"), patch(
        "main.get_confirmation_by_bot_message_id",
        return_value=_expense_confirmation(),
    ), patch(
        "main.process_reply_edit",
        AsyncMock(return_value=ReplyEditResult(text="Updated Lunch to ¥3800")),
    ) as edit_mock:
        response = post_signed(client, body)

    assert_callback_ok(response)
    edit_mock.assert_awaited()
    reply_mock.assert_awaited()
    message_text = reply_mock.call_args[0][0].messages[0].text
    assert "3800" in message_text
