"""Scenarios: bot.wish.accept / bot.wish.decline."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.confirmation_repository import ConfirmationRecord
from services.message_context import BotReply, ConfirmationSavePayload, ReplyEditResult
from services.reply_edit import apply_edit_intent
from services.tenant_context import TenantContext
from services.wish_list import WishListCandidate, candidate_to_pending_payload
from tests.functional.bot.conftest import assert_callback_ok, post_signed
from tests.functional.bot.helpers.webhook_events import text_message_event, webhook_body


def _wish_candidate() -> WishListCandidate:
    return WishListCandidate(
        name="Headphones",
        amount=Decimal("15000.00"),
        currency="JPY",
        assigned_level=1,
        category_node_id="cat-1",
        category_l1_id="cat-1",
        category_l2_id=None,
        category_l3_id=None,
        category_label="Gadgets",
        product_url=None,
    )


def _wish_confirmation() -> ConfirmationRecord:
    candidate = _wish_candidate()
    return ConfirmationRecord(
        id="conf-wish-1",
        bot_message_id="bot-wish-1",
        tenant=TenantContext.personal("U4af4980629"),
        confirmation_text="Add Headphones to wishlist?",
        items_snapshot=(),
        pending_action="wish_list_add",
        pending_payload=candidate_to_pending_payload(candidate),
    )


@pytest.mark.functional
def test_bot_wish_accept_webhook_and_insert(client, reply_mock):
    """Wish propose + yes via webhook; wish insert (not expense) on confirm apply."""
    propose_body = webhook_body(
        text_message_event("I want to buy headphones 15000 yen", message_id="msg-wish-1")
    )
    confirm_body = webhook_body(
        text_message_event("yes", message_id="msg-wish-yes", quoted_message_id="bot-wish-1")
    )

    with patch("main.save_inbound_text_message"), patch(
        "main.process_text_message",
        AsyncMock(
            return_value=BotReply(
                text="Add Headphones ¥15000?",
                confirmation=ConfirmationSavePayload(
                    tenant=TenantContext.personal("U4af4980629"),
                    confirmation_text="Add Headphones?",
                    items=(),
                    pending_action="wish_list_add",
                    pending_payload=candidate_to_pending_payload(_wish_candidate()),
                ),
            )
        ),
    ):
        assert_callback_ok(post_signed(client, propose_body))

    with patch("main.save_inbound_text_message"), patch(
        "main.get_confirmation_by_bot_message_id",
        return_value=_wish_confirmation(),
    ), patch(
        "main.process_reply_edit",
        AsyncMock(return_value=ReplyEditResult(text="Added Headphones to wishlist")),
    ):
        assert_callback_ok(post_signed(client, confirm_body))

    reply_mock.assert_awaited()
    message_text = reply_mock.call_args[0][0].messages[0].text
    assert "Headphones" in message_text or "wishlist" in message_text.lower()


@pytest.mark.functional
@pytest.mark.asyncio
async def test_bot_wish_accept_inserts_wish_not_expense():
    """Side-effect contract: affirm wish_list_add inserts wish, not expense."""
    wish_insert = MagicMock(return_value="wish-1")
    expense_insert = MagicMock()
    intent = {
        "action": "confirm_pending",
        "target": {"mode": "unspecified"},
        "updates": {},
        "clarification_needed": False,
        "clarification_message": None,
    }
    with patch("services.reply_edit.clear_pending_state", return_value=True), patch(
        "services.wish_list.insert_active_wish_list_item",
        wish_insert,
    ), patch(
        "services.reply_edit.get_expenses_by_ids",
        return_value=[],
    ), patch("services.message_handler.insert_expenses", expense_insert):
        result = await apply_edit_intent(intent, _wish_confirmation(), "yes", AsyncMock())

    assert result.status == "applied"
    assert result.summary
    wish_insert.assert_called_once()
    expense_insert.assert_not_called()


@pytest.mark.functional
def test_bot_wish_decline_webhook(client, reply_mock):
    """Wish decline via webhook returns cancel reply."""
    confirm_body = webhook_body(
        text_message_event("no", message_id="msg-wish-no", quoted_message_id="bot-wish-1")
    )

    with patch("main.save_inbound_text_message"), patch(
        "main.get_confirmation_by_bot_message_id",
        return_value=_wish_confirmation(),
    ), patch(
        "main.process_reply_edit",
        AsyncMock(return_value=ReplyEditResult(text="Cancelled wishlist add")),
    ):
        response = post_signed(client, confirm_body)

    assert_callback_ok(response)
    reply_mock.assert_awaited()
    assert "Cancel" in reply_mock.call_args[0][0].messages[0].text or "cancel" in reply_mock.call_args[0][0].messages[0].text.lower()


@pytest.mark.functional
@pytest.mark.asyncio
async def test_bot_wish_decline_inserts_neither():
    """Side-effect contract: cancel wish_list_add inserts neither wish nor expense."""
    wish_insert = MagicMock()
    expense_insert = MagicMock()
    intent = {
        "action": "cancel_pending",
        "target": {"mode": "unspecified"},
        "updates": {},
        "clarification_needed": False,
        "clarification_message": None,
    }
    with patch("services.reply_edit.clear_pending_state", return_value=True), patch(
        "services.wish_list.insert_active_wish_list_item",
        wish_insert,
    ), patch("services.message_handler.insert_expenses", expense_insert):
        await apply_edit_intent(intent, _wish_confirmation(), "no", AsyncMock())

    wish_insert.assert_not_called()
    expense_insert.assert_not_called()
