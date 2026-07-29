"""Scenario: bot.expense.text_confirm."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.categorize import CategoryResultWithProvenance
from services.expense_repository import PersistResult
from tests.functional.bot.conftest import assert_callback_ok, post_signed
from tests.functional.bot.helpers.webhook_events import text_message_event, webhook_body


def _unknown_category():
    return CategoryResultWithProvenance(guessed="unknown", alternatives=(), source="llm")


@pytest.mark.functional
def test_bot_expense_text_confirm(client, reply_mock):
    """Signed expense text → confirmation-style reply; insert_expenses called."""
    body = webhook_body(text_message_event("Lunch 1200 yen", message_id="msg-expense-1"))
    insert_mock = MagicMock(return_value=PersistResult(inserted=1, skipped=0))

    with patch("main.save_inbound_text_message"), patch(
        "services.message_handler.classify_text_message_intent",
        AsyncMock(return_value="expense"),
    ), patch(
        "services.message_handler.parse_text_for_expenses",
        return_value=[{"description": "Lunch", "amount": 1200.0, "currency": "JPY"}],
    ), patch(
        "services.message_handler.classify_expense_with_memory",
        AsyncMock(return_value=_unknown_category()),
    ), patch(
        "services.message_handler.insert_expenses",
        insert_mock,
    ):
        response = post_signed(client, body)

    assert_callback_ok(response)
    insert_mock.assert_called()
    reply_mock.assert_awaited()
    message_text = reply_mock.call_args[0][0].messages[0].text
    assert "Lunch" in message_text or "✅" in message_text
