"""LINE Messaging API profile helpers."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


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
