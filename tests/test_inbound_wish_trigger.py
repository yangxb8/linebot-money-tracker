from datetime import datetime, timezone
from unittest.mock import patch

from services.inbound_message_repository import (
    InboundMessageRecord,
    has_recent_wish_list_trigger_text,
)
from services.tenant_context import TenantContext


def test_has_recent_wish_list_trigger_text_true():
    tenant = TenantContext.personal('user-1')
    record = InboundMessageRecord(
        message_id='msg-1',
        line_user_id='user-1',
        tenant_type='user',
        tenant_id='user-1',
        message_type='text',
        text_content='想买这个',
        created_at=datetime.now(timezone.utc),
    )
    with patch(
        'services.inbound_message_repository.find_recent_inbound_text_messages',
        return_value=[record],
    ):
        assert has_recent_wish_list_trigger_text(tenant, within_seconds=30) is True


def test_has_recent_wish_list_trigger_text_false_for_normal_expense():
    tenant = TenantContext.personal('user-1')
    record = InboundMessageRecord(
        message_id='msg-2',
        line_user_id='user-1',
        tenant_type='user',
        tenant_id='user-1',
        message_type='text',
        text_content='午餐 1200円',
        created_at=datetime.now(timezone.utc),
    )
    with patch(
        'services.inbound_message_repository.find_recent_inbound_text_messages',
        return_value=[record],
    ):
        assert has_recent_wish_list_trigger_text(tenant, within_seconds=30) is False
