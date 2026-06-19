from __future__ import annotations

import logging
import re
from typing import Awaitable, Callable, Optional

from services.confirmation_i18n import t
from services.gemini_client import GeminiClient
from services.inbound_message_repository import get_failure_retry_anchor, get_inbound_message
from services.message_context import BotReply, MessageContext, RetryContext
from services.message_handler import process_image_message, process_text_message
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)

_RETRY_INTENT_RE = re.compile(
    r'^(?:'
    r'retry|try\s+again|again|'
    r'もう一度|もういちど|再試行|'
    r'重试|再试'
    r')\s*[.!。！]*$',
    re.IGNORECASE,
)


def is_retry_intent(text: str) -> bool:
    return bool(_RETRY_INTENT_RE.match((text or '').strip()))


def retry_not_found_reply(language: str = 'ja') -> str:
    return t(language, 'retry_not_found')


def retry_expired_reply(language: str = 'ja') -> str:
    return t(language, 'retry_expired')


def retry_image_expired_reply(language: str = 'ja') -> str:
    return t(language, 'retry_image_expired')


def _tenant_for_anchor(anchor) -> TenantContext:
    return TenantContext(
        tenant_type=anchor.tenant_type,
        tenant_id=anchor.tenant_id,
        logged_by_line_user_id=anchor.original_line_user_id,
    )


async def process_message_retry(
    retry_context: RetryContext,
    gemini: GeminiClient,
    fetch_image_bytes: Callable[[str], Awaitable[bytes]],
    *,
    logged_by_display_name: Optional[str] = None,
) -> BotReply:
    language = retry_context.reply_language
    anchor = get_failure_retry_anchor(
        retry_context.bot_error_message_id,
        retry_context.tenant,
    )
    if anchor is None:
        return BotReply(text=retry_not_found_reply(language))

    inbound = get_inbound_message(anchor.original_message_id)
    if inbound is None:
        return BotReply(text=retry_expired_reply(language))

    original_tenant = _tenant_for_anchor(anchor)
    message_context = MessageContext(
        tenant=original_tenant,
        source_message_id=anchor.original_message_id,
        reply_language=language,
        logged_by_display_name=logged_by_display_name if original_tenant.is_shared else None,
    )

    if inbound.message_type == 'text':
        text = (inbound.text_content or '').strip()
        if not text:
            logger.warning(
                'Retry anchor %s references empty text inbound %s',
                anchor.bot_error_message_id,
                anchor.original_message_id,
            )
            return BotReply(text=retry_expired_reply(language))
        logger.info(
            'Retrying text message original_message_id=%s via bot_error_message_id=%s',
            anchor.original_message_id,
            anchor.bot_error_message_id,
        )
        return await process_text_message(text, gemini, message_context)

    if inbound.message_type == 'image':
        try:
            image_bytes = await fetch_image_bytes(anchor.original_message_id)
        except Exception:
            logger.exception(
                'Retry image fetch failed original_message_id=%s',
                anchor.original_message_id,
            )
            return BotReply(text=retry_image_expired_reply(language))
        logger.info(
            'Retrying image message original_message_id=%s via bot_error_message_id=%s',
            anchor.original_message_id,
            anchor.bot_error_message_id,
        )
        return await process_image_message(image_bytes, gemini, context=message_context)

    logger.warning('Unsupported inbound message_type=%s for retry', inbound.message_type)
    return BotReply(text=retry_expired_reply(language))
