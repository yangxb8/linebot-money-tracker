from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)

INBOUND_MESSAGE_TTL_DAYS = 7


@dataclass(frozen=True)
class InboundMessageRecord:
    message_id: str
    line_user_id: str
    tenant_type: str
    tenant_id: str
    message_type: str
    text_content: Optional[str]
    created_at: datetime


@dataclass(frozen=True)
class FailureRetryAnchor:
    bot_error_message_id: str
    original_message_id: str
    original_line_user_id: str
    tenant_type: str
    tenant_id: str
    failure_kind: str


def _ttl_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=INBOUND_MESSAGE_TTL_DAYS)


def _parse_timestamp(raw: object) -> datetime:
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw
    text = str(raw).strip()
    if text.endswith('Z'):
        text = f'{text[:-1]}+00:00'
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def purge_expired_inbound_messages() -> None:
    if not is_supabase_configured():
        return
    try:
        client = get_supabase_client()
        client.table('inbound_messages').delete().lt(
            'created_at',
            _ttl_cutoff().isoformat(),
        ).execute()
    except Exception:
        logger.exception('purge_expired_inbound_messages failed')


def save_inbound_text_message(
    *,
    message_id: str,
    line_user_id: str,
    tenant: TenantContext,
    text_content: str,
) -> None:
    purge_expired_inbound_messages()
    if not is_supabase_configured():
        return
    try:
        client = get_supabase_client()
        client.table('inbound_messages').upsert(
            {
                'message_id': message_id,
                'line_user_id': line_user_id,
                'tenant_type': tenant.tenant_type,
                'tenant_id': tenant.tenant_id,
                'message_type': 'text',
                'text_content': text_content,
            },
            on_conflict='message_id',
        ).execute()
    except Exception:
        logger.exception('save_inbound_text_message failed message_id=%s', message_id)


def save_inbound_image_message(
    *,
    message_id: str,
    line_user_id: str,
    tenant: TenantContext,
) -> None:
    purge_expired_inbound_messages()
    if not is_supabase_configured():
        return
    try:
        client = get_supabase_client()
        client.table('inbound_messages').upsert(
            {
                'message_id': message_id,
                'line_user_id': line_user_id,
                'tenant_type': tenant.tenant_type,
                'tenant_id': tenant.tenant_id,
                'message_type': 'image',
                'text_content': None,
            },
            on_conflict='message_id',
        ).execute()
    except Exception:
        logger.exception('save_inbound_image_message failed message_id=%s', message_id)


def find_recent_inbound_text_messages(
    tenant: TenantContext,
    *,
    within_seconds: int,
) -> list[InboundMessageRecord]:
    """Return recent text inbound messages for this sender+ledger, newest first."""
    if not is_supabase_configured():
        return []

    try:
        client = get_supabase_client()
        threshold = datetime.now(timezone.utc) - timedelta(seconds=within_seconds)
        response = (
            client.table('inbound_messages')
            .select('*')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .eq('line_user_id', tenant.logged_by_line_user_id)
            .eq('message_type', 'text')
            .gte('created_at', threshold.isoformat())
            .order('created_at', desc=True)
            .execute()
        )
        records: list[InboundMessageRecord] = []
        for row in response.data or []:
            created_at = _parse_timestamp(row.get('created_at'))
            if created_at < _ttl_cutoff():
                continue
            records.append(
                InboundMessageRecord(
                    message_id=str(row['message_id']),
                    line_user_id=str(row['line_user_id']),
                    tenant_type=str(row['tenant_type']),
                    tenant_id=str(row['tenant_id']),
                    message_type=str(row['message_type']),
                    text_content=row.get('text_content'),
                    created_at=created_at,
                )
            )
        return records
    except Exception:
        logger.exception('find_recent_inbound_text_messages failed')
        return []


def has_recent_wish_list_trigger_text(
    tenant: TenantContext,
    *,
    within_seconds: int = 30,
) -> bool:
    """True when the sender recently posted wish-list trigger text on this ledger."""
    from services.wish_list import looks_like_wish_list_intent

    for record in find_recent_inbound_text_messages(tenant, within_seconds=within_seconds):
        if looks_like_wish_list_intent(record.text_content):
            return True
    return False


def get_inbound_message(message_id: str) -> Optional[InboundMessageRecord]:
    purge_expired_inbound_messages()
    if not is_supabase_configured():
        return None
    try:
        client = get_supabase_client()
        response = (
            client.table('inbound_messages')
            .select('*')
            .eq('message_id', message_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        row = rows[0]
        created_at = _parse_timestamp(row.get('created_at'))
        if created_at < _ttl_cutoff():
            return None
        return InboundMessageRecord(
            message_id=str(row['message_id']),
            line_user_id=str(row['line_user_id']),
            tenant_type=str(row['tenant_type']),
            tenant_id=str(row['tenant_id']),
            message_type=str(row['message_type']),
            text_content=row.get('text_content'),
            created_at=created_at,
        )
    except Exception:
        logger.exception('get_inbound_message failed message_id=%s', message_id)
        return None


def save_failure_retry_anchor(
    *,
    bot_error_message_id: str,
    original_message_id: str,
    original_line_user_id: str,
    tenant: TenantContext,
    failure_kind: str,
) -> None:
    if not is_supabase_configured():
        return
    try:
        client = get_supabase_client()
        client.table('failure_retry_anchors').upsert(
            {
                'bot_error_message_id': bot_error_message_id,
                'original_message_id': original_message_id,
                'original_line_user_id': original_line_user_id,
                'tenant_type': tenant.tenant_type,
                'tenant_id': tenant.tenant_id,
                'failure_kind': failure_kind,
            },
            on_conflict='bot_error_message_id',
        ).execute()
        logger.info(
            'Saved failure retry anchor bot_error_message_id=%s original_message_id=%s',
            bot_error_message_id,
            original_message_id,
        )
    except Exception:
        logger.exception(
            'save_failure_retry_anchor failed bot_error_message_id=%s',
            bot_error_message_id,
        )


def get_failure_retry_anchor(
    bot_error_message_id: str,
    tenant: TenantContext,
) -> Optional[FailureRetryAnchor]:
    purge_expired_inbound_messages()
    if not is_supabase_configured():
        return None
    try:
        client = get_supabase_client()
        response = (
            client.table('failure_retry_anchors')
            .select('*')
            .eq('bot_error_message_id', bot_error_message_id)
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        row = rows[0]
        created_at = _parse_timestamp(row.get('created_at'))
        if created_at < _ttl_cutoff():
            return None
        return FailureRetryAnchor(
            bot_error_message_id=str(row['bot_error_message_id']),
            original_message_id=str(row['original_message_id']),
            original_line_user_id=str(row['original_line_user_id']),
            tenant_type=str(row['tenant_type']),
            tenant_id=str(row['tenant_id']),
            failure_kind=str(row['failure_kind']),
        )
    except Exception:
        logger.exception(
            'get_failure_retry_anchor failed bot_error_message_id=%s',
            bot_error_message_id,
        )
        return None
