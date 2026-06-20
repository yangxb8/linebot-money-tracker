"""LINE Messaging API helpers for group/room chat metadata."""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.tenant_context import TENANT_GROUP, TenantContext

logger = logging.getLogger(__name__)


def _summary_name(summary: Any) -> Optional[str]:
    group_name = getattr(summary, 'group_name', None) or getattr(summary, 'groupName', None)
    if isinstance(group_name, str) and group_name.strip():
        return group_name.strip()
    return None


async def fetch_chat_display_name(
    messaging_api: Any,
    tenant: TenantContext,
) -> Optional[str]:
    """Resolve the shared chat title shown in the expense dashboard."""
    if messaging_api is None or not tenant.is_shared:
        return None

    try:
        if tenant.tenant_type == TENANT_GROUP:
            summary = await messaging_api.get_group_summary(tenant.tenant_id)
            return _summary_name(summary)
    except Exception:
        logger.warning(
            'fetch_chat_display_name failed tenant=%s id=%s',
            tenant.tenant_type,
            tenant.tenant_id,
            exc_info=True,
        )
    return None
