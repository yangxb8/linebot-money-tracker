"""Pre-LLM usage guards: payload, rate limits, quota resolution."""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from services.tenant_context import TenantContext
from services.usage_config import get_free_tier_limits
from services.usage_limit_i18n import usage_limit_message
from services.usage_metering import UsageBillingContext
from services.usage_repository import (
    count_sender_messages_in_window,
    has_quota_headroom,
    is_usage_tracking_enabled,
    list_eligible_donors,
    upsert_tenant_chat_member,
)

logger = logging.getLogger(__name__)


class LimitDenyReason(str, Enum):
    PAYLOAD_TEXT = 'payload_too_large_text'
    PAYLOAD_IMAGE = 'payload_too_large_image'
    RATE_MINUTE = 'user_rate_limit_minute'
    RATE_DAY = 'user_rate_limit_day'
    QUOTA_MONTHLY = 'user_quota_monthly'
    RECEIPT_QUOTA_MONTHLY = 'user_receipt_quota_monthly'


@dataclass(frozen=True)
class LimitCheckResult:
    allowed: bool
    reason: Optional[LimitDenyReason] = None
    billing_context: Optional[UsageBillingContext] = None


def count_words(text: str) -> int:
    return len(re.findall(r'\S+', text or ''))


def check_payload_text(text: str) -> Optional[LimitDenyReason]:
    limits = get_free_tier_limits()
    if count_words(text) > limits.max_text_words:
        return LimitDenyReason.PAYLOAD_TEXT
    return None


def check_payload_image(image_bytes: bytes) -> Optional[LimitDenyReason]:
    limits = get_free_tier_limits()
    if len(image_bytes) > limits.max_image_bytes:
        return LimitDenyReason.PAYLOAD_IMAGE
    return None


def check_sender_rate_limits(sender_line_user_id: str) -> Optional[LimitDenyReason]:
    if not is_usage_tracking_enabled():
        return None
    limits = get_free_tier_limits()
    try:
        minute_count = count_sender_messages_in_window(sender_line_user_id, window_seconds=60)
        if minute_count >= limits.rate_per_minute:
            return LimitDenyReason.RATE_MINUTE
        day_count = count_sender_messages_in_window(sender_line_user_id, window_seconds=86400)
        if day_count >= limits.rate_per_day:
            return LimitDenyReason.RATE_DAY
    except Exception:
        if is_usage_tracking_enabled():
            logger.exception('rate limit check failed; failing closed')
            return LimitDenyReason.QUOTA_MONTHLY
    return None


def resolve_billing_user(
    tenant: TenantContext,
    sender_line_user_id: str,
    *,
    needs_receipt: bool,
    source_message_id: Optional[str],
    reply_language: str = 'ja',
) -> Optional[UsageBillingContext]:
    if has_quota_headroom(sender_line_user_id, needs_receipt=needs_receipt):
        return UsageBillingContext(
            billing_line_user_id=sender_line_user_id,
            sender_line_user_id=sender_line_user_id,
            source_message_id=source_message_id,
            tenant_type=tenant.tenant_type,
            tenant_id=tenant.tenant_id,
            pooled=False,
            reply_language=reply_language,
            needs_receipt_headroom=needs_receipt,
        )

    if not tenant.is_shared:
        return None

    try:
        donors = list_eligible_donors(tenant, sender_line_user_id, needs_receipt=needs_receipt)
    except Exception:
        logger.exception('donor lookup failed; failing closed')
        return None

    if not donors:
        return None

    donor = random.choice(donors)
    return UsageBillingContext(
        billing_line_user_id=donor,
        sender_line_user_id=sender_line_user_id,
        source_message_id=source_message_id,
        tenant_type=tenant.tenant_type,
        tenant_id=tenant.tenant_id,
        pooled=True,
        reply_language=reply_language,
        needs_receipt_headroom=needs_receipt,
    )


def format_denial_reply(language: str, reason: LimitDenyReason) -> str:
    limits = get_free_tier_limits()
    if reason == LimitDenyReason.PAYLOAD_TEXT:
        return usage_limit_message(language, reason.value, max_words=str(limits.max_text_words))
    if reason == LimitDenyReason.PAYLOAD_IMAGE:
        max_mb = limits.max_image_bytes // (1024 * 1024)
        return usage_limit_message(language, reason.value, max_mb=str(max_mb))
    return usage_limit_message(language, reason.value)


def prepare_inbound_usage(
    tenant: TenantContext,
    sender_line_user_id: str,
    source_message_id: Optional[str],
    *,
    reply_language: str = 'ja',
    text: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    skip_limits: bool = False,
) -> LimitCheckResult:
    if skip_limits or not is_usage_tracking_enabled():
        return LimitCheckResult(
            allowed=True,
            billing_context=UsageBillingContext(
                billing_line_user_id=sender_line_user_id,
                sender_line_user_id=sender_line_user_id,
                source_message_id=source_message_id,
                tenant_type=tenant.tenant_type,
                tenant_id=tenant.tenant_id,
                pooled=False,
                reply_language=reply_language,
                needs_receipt_headroom=image_bytes is not None,
            ),
        )

    upsert_tenant_chat_member(tenant, sender_line_user_id)

    if text is not None:
        payload_reason = check_payload_text(text)
        if payload_reason:
            return LimitCheckResult(allowed=False, reason=payload_reason)

    if image_bytes is not None:
        payload_reason = check_payload_image(image_bytes)
        if payload_reason:
            return LimitCheckResult(allowed=False, reason=payload_reason)

    rate_reason = check_sender_rate_limits(sender_line_user_id)
    if rate_reason:
        return LimitCheckResult(allowed=False, reason=rate_reason)

    needs_receipt = image_bytes is not None
    billing = resolve_billing_user(
        tenant,
        sender_line_user_id,
        needs_receipt=needs_receipt,
        source_message_id=source_message_id,
        reply_language=reply_language,
    )
    if billing is None:
        if needs_receipt and has_quota_headroom(sender_line_user_id, needs_receipt=False):
            if not has_quota_headroom(sender_line_user_id, needs_receipt=True):
                return LimitCheckResult(allowed=False, reason=LimitDenyReason.RECEIPT_QUOTA_MONTHLY)
        return LimitCheckResult(allowed=False, reason=LimitDenyReason.QUOTA_MONTHLY)

    return LimitCheckResult(allowed=True, billing_context=billing)


def check_billing_headroom_for_operation(
    billing: UsageBillingContext,
    operation_type: str,
) -> Optional[LimitDenyReason]:
    if not is_usage_tracking_enabled():
        return None
    needs_receipt = operation_type == 'receipt_analysis'
    try:
        if not has_quota_headroom(billing.billing_line_user_id, needs_receipt=needs_receipt):
            if needs_receipt:
                return LimitDenyReason.RECEIPT_QUOTA_MONTHLY
            return LimitDenyReason.QUOTA_MONTHLY
    except Exception:
        logger.exception('quota re-check failed; failing closed')
        return LimitDenyReason.QUOTA_MONTHLY
    return None
