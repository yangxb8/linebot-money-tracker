from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.confirmation_repository import ConfirmationRecord
from services.message_context import ConfirmationSavePayload, MessageContext
from services.tenant_context import TenantContext
from services.wish_list import WishBudgetImpact


def _pending_confirmation() -> ConfirmationRecord:
    tenant = TenantContext.personal('user-1')
    return ConfirmationRecord(
        id='conf-await',
        bot_message_id='bot-await',
        tenant=tenant,
        confirmation_text='await details',
        items_snapshot=(),
        pending_action='wish_list_await_details',
        pending_payload={},
    )


@pytest.mark.asyncio
async def test_image_pending_routes_to_wish_and_clears_on_add():
    tenant = TenantContext.personal('user-1')
    context = MessageContext(
        tenant=tenant,
        source_message_id='msg-img-1',
        reply_language='en',
    )

    pending = _pending_confirmation()

    proposal_confirmation = ConfirmationSavePayload(
        tenant=tenant,
        confirmation_text='Add?',
        items=(),
        pending_action='wish_list_add',
        pending_payload={},
    )

    with patch(
        'services.message_handler.get_latest_pending_confirmation',
        return_value=pending,
    ), patch(
        'services.message_handler._extract_expense_items_from_image',
        AsyncMock(return_value=[{'amount': 24000, 'description': 'X'}]),
    ), patch(
        'services.message_handler._wish_list_reply_from_items',
        AsyncMock(return_value=MagicMock(text='proposal', confirmation=proposal_confirmation)),
    ), patch(
        'services.message_handler._enrich_and_persist_items',
        AsyncMock(side_effect=AssertionError('must not persist')),
    ), patch(
        'services.message_handler.clear_pending_state',
        return_value=True,
    ):
        from services.message_handler import process_image_message

        await process_image_message(b'img', AsyncMock(), mime_type='image/jpeg', context=context)


@pytest.mark.asyncio
async def test_image_pending_does_not_clear_when_still_awaiting_details():
    tenant = TenantContext.personal('user-1')
    context = MessageContext(
        tenant=tenant,
        source_message_id='msg-img-2',
        reply_language='en',
    )

    pending = _pending_confirmation()

    await_confirmation = ConfirmationSavePayload(
        tenant=tenant,
        confirmation_text='await',
        items=(),
        pending_action='wish_list_await_details',
        pending_payload={},
    )

    with patch(
        'services.message_handler.get_latest_pending_confirmation',
        return_value=pending,
    ), patch(
        'services.message_handler._extract_expense_items_from_image',
        AsyncMock(return_value=[{'amount': 0, 'description': 'X'}]),
    ), patch(
        'services.message_handler._wish_list_reply_from_items',
        AsyncMock(return_value=MagicMock(text='await', confirmation=await_confirmation)),
    ), patch(
        'services.message_handler._enrich_and_persist_items',
        AsyncMock(side_effect=AssertionError('must not persist')),
    ), patch(
        'services.message_handler.clear_pending_state',
        return_value=True,
    ) as clear_mock:
        from services.message_handler import process_image_message

        await process_image_message(b'img', AsyncMock(), mime_type='image/jpeg', context=context)
        clear_mock.assert_not_called()

