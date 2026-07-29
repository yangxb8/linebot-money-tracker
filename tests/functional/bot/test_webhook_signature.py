"""Scenario: bot.webhook.unsigned (+ valid-signature companion)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.message_context import BotReply
from tests.functional.bot.conftest import assert_callback_ok, post_callback, post_signed
from tests.functional.bot.helpers.webhook_events import text_message_event, webhook_body


@pytest.mark.functional
def test_bot_webhook_unsigned_returns_400(client, reply_mock):
    """bot.webhook.unsigned — missing signature → 400, no reply."""
    body = webhook_body(text_message_event("Lunch 1200 yen"))
    response = post_callback(client, body, signature=None)
    assert response.status_code == 400
    reply_mock.assert_not_called()


@pytest.mark.functional
def test_bot_webhook_invalid_signature_returns_400(client, reply_mock):
    """bot.webhook.unsigned — invalid signature → 400, no reply."""
    body = webhook_body(text_message_event("Lunch 1200 yen"))
    response = post_callback(client, body, signature="not-a-valid-signature")
    assert response.status_code == 400
    reply_mock.assert_not_called()


@pytest.mark.functional
def test_bot_webhook_valid_signature_reaches_handler(client, reply_mock):
    """Valid HMAC allows parse path; handler mocked downstream."""
    body = webhook_body(text_message_event("Lunch 1200 yen"))
    with patch(
        "main.process_text_message",
        AsyncMock(return_value=BotReply(text="✅ Lunch ¥1200")),
    ), patch("main.save_inbound_text_message"):
        response = post_signed(client, body)

    assert_callback_ok(response)
    reply_mock.assert_awaited()
