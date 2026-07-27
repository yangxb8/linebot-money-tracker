from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.confirmation_repository import ConfirmationRecord
from services.message_context import MessageContext, ReplyContext
from services.message_handler import (
    _handle_wish_list_await_details_text,
    process_reply_wish_list_image,
)
from services.tenant_context import TenantContext
from services.wish_list import (
    WishListCandidate,
    build_wish_list_await_details_reply,
    candidate_to_pending_payload,
    format_wish_list_ask_details,
)


def _await_confirmation() -> ConfirmationRecord:
    return ConfirmationRecord(
        id='conf-await',
        bot_message_id='bot-await',
        tenant=TenantContext.personal('user-1'),
        confirmation_text=format_wish_list_ask_details('zh'),
        items_snapshot=(),
        pending_action='wish_list_await_details',
        pending_payload={},
    )


def test_await_details_reply_payload():
    context = MessageContext(
        tenant=TenantContext.personal('user-1'),
        source_message_id='msg-1',
        reply_language='zh',
    )
    reply = build_wish_list_await_details_reply(context)
    assert reply.confirmation is not None
    assert reply.confirmation.pending_action == 'wish_list_await_details'
    assert '商品' in reply.text or '图片' in reply.text


@pytest.mark.asyncio
async def test_await_details_cancel():
    confirmation = _await_confirmation()
    reply_context = ReplyContext(
        tenant=confirmation.tenant,
        user_reply_message_id='reply-1',
        quoted_bot_message_id=confirmation.bot_message_id,
        reply_language='en',
    )
    with patch('services.message_handler.clear_pending_state') as clear_mock, patch(
        'services.message_handler.write_audit',
    ):
        result = await _handle_wish_list_await_details_text(
            'no',
            confirmation,
            reply_context,
            AsyncMock(),
            'en',
        )
    assert 'cancel' in result.text.lower() or 'Wishlist' in result.text
    clear_mock.assert_called_once_with(confirmation.id)
    assert result.anchor_reply_to_sent_message is False


@pytest.mark.asyncio
async def test_await_details_text_promotes_to_wish_list_add():
    confirmation = _await_confirmation()
    reply_context = ReplyContext(
        tenant=confirmation.tenant,
        user_reply_message_id='reply-2',
        quoted_bot_message_id=confirmation.bot_message_id,
        reply_language='en',
    )
    candidate = WishListCandidate(
        name='Headphones',
        amount=Decimal('15000.00'),
        currency='JPY',
        assigned_level=1,
        category_node_id='c1',
        category_l1_id='c1',
        category_l2_id=None,
        category_l3_id=None,
        category_label='Gadgets',
        product_url=None,
    )
    from services.message_context import BotReply, ConfirmationSavePayload

    proposal = BotReply(
        text='Add Headphones?',
        confirmation=ConfirmationSavePayload(
            tenant=confirmation.tenant,
            confirmation_text='Add Headphones?',
            items=(),
            pending_action='wish_list_add',
            pending_payload=candidate_to_pending_payload(candidate),
        ),
    )
    with patch(
        'services.message_handler.process_wish_list_details_from_text',
        AsyncMock(return_value=proposal),
    ), patch('services.message_handler.set_pending_state') as set_mock, patch(
        'services.message_handler.write_audit',
    ):
        result = await _handle_wish_list_await_details_text(
            'Headphones 15000 yen',
            confirmation,
            reply_context,
            AsyncMock(),
            'en',
        )

    assert result.text == 'Add Headphones?'
    assert result.anchor_reply_to_sent_message is True
    set_mock.assert_called_once()
    assert set_mock.call_args.args[1] == 'wish_list_add'


@pytest.mark.asyncio
async def test_await_details_image_promotes_to_wish_list_add():
    confirmation = _await_confirmation()
    reply_context = ReplyContext(
        tenant=confirmation.tenant,
        user_reply_message_id='reply-img',
        quoted_bot_message_id=confirmation.bot_message_id,
        reply_language='zh',
    )
    candidate = WishListCandidate(
        name='PlayStation Portal',
        amount=Decimal('24000.00'),
        currency='JPY',
        assigned_level=2,
        category_node_id='c2',
        category_l1_id='c1',
        category_l2_id='c2',
        category_l3_id=None,
        category_label='休闲 > 电子游戏',
        product_url=None,
    )
    from services.message_context import BotReply, ConfirmationSavePayload

    proposal = BotReply(
        text='愿望单候选项',
        confirmation=ConfirmationSavePayload(
            tenant=confirmation.tenant,
            confirmation_text='愿望单候选项',
            items=(),
            pending_action='wish_list_add',
            pending_payload=candidate_to_pending_payload(candidate),
        ),
    )
    with patch(
        'services.message_handler.try_mark_reply_processed',
        return_value=True,
    ), patch(
        'services.message_handler.get_confirmation_by_bot_message_id',
        return_value=confirmation,
    ), patch(
        'services.message_handler.process_wish_list_details_from_image',
        AsyncMock(return_value=proposal),
    ), patch('services.message_handler.set_pending_state') as set_mock, patch(
        'services.message_handler.write_audit',
    ):
        result = await process_reply_wish_list_image(b'fake-image', reply_context, AsyncMock())

    assert '愿望单' in result.text
    assert result.anchor_reply_to_sent_message is True
    set_mock.assert_called_once()
    assert set_mock.call_args.args[1] == 'wish_list_add'
