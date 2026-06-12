"""LINE Messaging API profile helpers."""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.tenant_context import TENANT_GROUP, TENANT_ROOM, TenantContext

logger = logging.getLogger(__name__)


def _profile_display_name(profile: Any) -> Optional[str]:
    display_name = getattr(profile, 'display_name', None) or getattr(profile, 'displayName', None)
    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()
    return None


async def fetch_line_display_name(
    messaging_api: Any,
    tenant: TenantContext,
    line_user_id: str,
) -> Optional[str]:
    """Resolve a LINE member display name for expense attribution."""
    if messaging_api is None or not line_user_id:
        return None
    try:
        if tenant.tenant_type == TENANT_GROUP:
            profile = await messaging_api.get_group_member_profile(tenant.tenant_id, line_user_id)
        elif tenant.tenant_type == TENANT_ROOM:
            profile = await messaging_api.get_room_member_profile(tenant.tenant_id, line_user_id)
        else:
            profile = await messaging_api.get_profile(line_user_id)
        return _profile_display_name(profile)
    except Exception:
        logger.warning(
            'fetch_line_display_name failed tenant=%s user=%s',
            tenant.tenant_type,
            line_user_id,
            exc_info=True,
        )
    return None


async def fetch_line_profile_language(messaging_api: Any, line_user_id: str) -> Optional[str]:
    if messaging_api is None or not line_user_id:
        return None
    try:
        profile = await messaging_api.get_profile(line_user_id)
        language = getattr(profile, 'language', None)
        if isinstance(language, str) and language.strip():
            return language.strip()
    except Exception:
        logger.warning('fetch_line_profile_language failed for user=%s', line_user_id, exc_info=True)
    return None
