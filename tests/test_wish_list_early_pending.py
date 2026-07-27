from unittest.mock import patch

from services.message_context import MessageContext
from services.tenant_context import TenantContext
from services.wish_list import persist_wish_list_await_details_pending


def test_persist_wish_list_await_details_pending_uses_trigger_message_id():
    tenant = TenantContext.personal('user-1')
    context = MessageContext(
        tenant=tenant,
        source_message_id='msg-text-1',
        reply_language='zh',
    )

    with patch(
        'services.wish_list.get_latest_pending_confirmation',
        return_value=None,
    ), patch(
        'services.wish_list.save_pending_confirmation',
        return_value='conf-early',
    ) as save_mock:
        confirmation_id = persist_wish_list_await_details_pending(context)

    assert confirmation_id == 'conf-early'
    save_mock.assert_called_once()
    assert save_mock.call_args.kwargs['bot_message_id'] == 'wish-await:msg-text-1'
    assert save_mock.call_args.kwargs['pending_action'] == 'wish_list_await_details'


def test_persist_wish_list_await_details_pending_reuses_existing():
    tenant = TenantContext.personal('user-1')
    context = MessageContext(
        tenant=tenant,
        source_message_id='msg-text-2',
        reply_language='zh',
    )
    existing = type(
        'Rec',
        (),
        {'id': 'conf-existing'},
    )()

    with patch(
        'services.wish_list.get_latest_pending_confirmation',
        return_value=existing,
    ), patch('services.wish_list.save_pending_confirmation') as save_mock:
        confirmation_id = persist_wish_list_await_details_pending(context)

    assert confirmation_id == 'conf-existing'
    save_mock.assert_not_called()
