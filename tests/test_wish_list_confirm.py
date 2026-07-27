from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.message_context import ConfirmationItemSnapshot
from services.confirmation_repository import ConfirmationRecord
from services.reply_edit import apply_edit_intent, parse_edit_intent
from services.tenant_context import TenantContext
from services.wish_list import WishListCandidate, candidate_to_pending_payload


def _wish_confirmation() -> ConfirmationRecord:
    candidate = WishListCandidate(
        name='Headphones',
        amount=Decimal('15000.00'),
        currency='JPY',
        assigned_level=1,
        category_node_id='cat-1',
        category_l1_id='cat-1',
        category_l2_id=None,
        category_l3_id=None,
        category_label='ガジェット',
        product_url=None,
    )
    return ConfirmationRecord(
        id='conf-1',
        bot_message_id='bot-1',
        tenant=TenantContext.personal('user-1'),
        confirmation_text='Add to wishlist?',
        items_snapshot=(),
        pending_action='wish_list_add',
        pending_payload=candidate_to_pending_payload(candidate),
    )


@pytest.mark.asyncio
async def test_parse_edit_intent_affirm_wish_list():
    intent = await parse_edit_intent('yes', [], 'wish_list_add', AsyncMock())
    assert intent['action'] == 'confirm_pending'


@pytest.mark.asyncio
async def test_parse_edit_intent_cancel_wish_list():
    intent = await parse_edit_intent('no', [], 'wish_list_add', AsyncMock())
    assert intent['action'] == 'cancel_pending'


@pytest.mark.asyncio
async def test_apply_confirm_uses_tenant_reply_language():
    confirmation = _wish_confirmation()
    intent = {
        'action': 'confirm_pending',
        'target': {'mode': 'unspecified'},
        'updates': {},
        'clarification_needed': False,
        'clarification_message': None,
    }
    with patch('services.reply_edit.clear_pending_state', return_value=True), patch(
        'services.wish_list.insert_active_wish_list_item',
        return_value='wish-1',
    ), patch(
        'services.reply_edit.get_expenses_by_ids',
        return_value=[],
    ), patch(
        'services.reply_edit.resolve_tenant_reply_language',
        return_value='zh',
    ):
        result = await apply_edit_intent(intent, confirmation, 'yes', AsyncMock())

    assert result.status == 'applied'
    assert '愿望单' in result.summary


@pytest.mark.asyncio
async def test_apply_confirm_inserts_wish_item_not_expense():
    confirmation = _wish_confirmation()
    intent = {
        'action': 'confirm_pending',
        'target': {'mode': 'unspecified'},
        'updates': {},
        'clarification_needed': False,
        'clarification_message': None,
    }
    with patch('services.reply_edit.clear_pending_state', return_value=True), patch(
        'services.wish_list.insert_active_wish_list_item',
        return_value='wish-1',
    ) as insert_mock, patch(
        'services.reply_edit.get_expenses_by_ids',
        return_value=[],
    ):
        result = await apply_edit_intent(intent, confirmation, 'yes', AsyncMock())

    assert result.status == 'applied'
    assert 'Headphones' in result.summary or 'ウィッシュ' in result.summary or 'wishlist' in result.summary.lower()
    insert_mock.assert_called_once()


@pytest.mark.asyncio
async def test_apply_cancel_does_not_insert():
    confirmation = _wish_confirmation()
    intent = {
        'action': 'cancel_pending',
        'target': {'mode': 'unspecified'},
        'updates': {},
        'clarification_needed': False,
        'clarification_message': None,
    }
    with patch('services.reply_edit.clear_pending_state', return_value=True) as clear_mock, patch(
        'services.wish_list.insert_active_wish_list_item',
    ) as insert_mock, patch(
        'services.reply_edit.get_expenses_by_ids',
        return_value=[],
    ):
        result = await apply_edit_intent(intent, confirmation, 'no', AsyncMock())

    assert result.status == 'applied'
    clear_mock.assert_called_once()
    insert_mock.assert_not_called()
