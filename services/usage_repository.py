"""Supabase persistence for per-user LLM usage metering."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext
from services.usage_config import LIFETIME_BUCKET, get_free_tier_limits

logger = logging.getLogger(__name__)

JST = __import__('zoneinfo').ZoneInfo('Asia/Tokyo')


def is_usage_tracking_enabled() -> bool:
    return is_supabase_configured()


def current_jst_year_month(now: Optional[datetime] = None) -> str:
    instant = now or datetime.now(JST)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=JST)
    else:
        instant = instant.astimezone(JST)
    return instant.strftime('%Y-%m')


@dataclass(frozen=True)
class UserUsageSnapshot:
    line_user_id: str
    jst_year_month: str
    month_invocations: int
    month_receipt_analyses: int
    lifetime_invocations: int


def _empty_snapshot(line_user_id: str) -> UserUsageSnapshot:
    return UserUsageSnapshot(
        line_user_id=line_user_id,
        jst_year_month=current_jst_year_month(),
        month_invocations=0,
        month_receipt_analyses=0,
        lifetime_invocations=0,
    )


def get_user_usage_snapshot(line_user_id: str) -> UserUsageSnapshot:
    if not is_usage_tracking_enabled():
        return _empty_snapshot(line_user_id)

    month = current_jst_year_month()
    try:
        client = get_supabase_client()
        month_resp = (
            client.table('user_usage_summary')
            .select('month_invocations, month_receipt_analyses')
            .eq('line_user_id', line_user_id)
            .eq('jst_year_month', month)
            .limit(1)
            .execute()
        )
        lifetime_resp = (
            client.table('user_usage_summary')
            .select('lifetime_invocations')
            .eq('line_user_id', line_user_id)
            .eq('jst_year_month', LIFETIME_BUCKET)
            .limit(1)
            .execute()
        )
        month_row = (month_resp.data or [None])[0] or {}
        lifetime_row = (lifetime_resp.data or [None])[0] or {}
        return UserUsageSnapshot(
            line_user_id=line_user_id,
            jst_year_month=month,
            month_invocations=int(month_row.get('month_invocations') or 0),
            month_receipt_analyses=int(month_row.get('month_receipt_analyses') or 0),
            lifetime_invocations=int(lifetime_row.get('lifetime_invocations') or 0),
        )
    except Exception:
        logger.exception('get_user_usage_snapshot failed for user=%s', line_user_id)
        raise


def has_quota_headroom(line_user_id: str, *, needs_receipt: bool) -> bool:
    limits = get_free_tier_limits()
    snap = get_user_usage_snapshot(line_user_id)
    if snap.month_invocations >= limits.monthly_total:
        return False
    if needs_receipt and snap.month_receipt_analyses >= limits.monthly_receipt_analyses:
        return False
    return True


def upsert_tenant_chat(tenant: TenantContext, display_name: Optional[str] = None) -> None:
    if not is_usage_tracking_enabled() or not tenant.is_shared:
        return
    try:
        client = get_supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        row: dict[str, str] = {
            'tenant_type': tenant.tenant_type,
            'tenant_id': tenant.tenant_id,
            'updated_at': now,
        }
        if display_name:
            row['display_name'] = display_name
        client.table('tenant_chats').upsert(
            row,
            on_conflict='tenant_type,tenant_id',
        ).execute()
    except Exception:
        logger.exception(
            'upsert_tenant_chat failed tenant=%s',
            tenant.tenant_id,
        )


def upsert_tenant_chat_member(
    tenant: TenantContext,
    line_user_id: str,
    *,
    display_name: Optional[str] = None,
) -> None:
    if not is_usage_tracking_enabled() or not tenant.is_shared:
        return
    try:
        upsert_tenant_chat(tenant, display_name)
        client = get_supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        client.table('tenant_chat_members').upsert(
            {
                'tenant_type': tenant.tenant_type,
                'tenant_id': tenant.tenant_id,
                'line_user_id': line_user_id,
                'last_seen_at': now,
            },
            on_conflict='tenant_type,tenant_id,line_user_id',
        ).execute()
    except Exception:
        logger.exception(
            'upsert_tenant_chat_member failed tenant=%s user=%s',
            tenant.tenant_id,
            line_user_id,
        )


def list_eligible_donors(
    tenant: TenantContext,
    sender_line_user_id: str,
    *,
    needs_receipt: bool,
) -> List[str]:
    if not is_usage_tracking_enabled() or not tenant.is_shared:
        return []
    try:
        client = get_supabase_client()
        resp = (
            client.table('tenant_chat_members')
            .select('line_user_id')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .neq('line_user_id', sender_line_user_id)
            .execute()
        )
        donors: List[str] = []
        for row in resp.data or []:
            candidate = str(row.get('line_user_id') or '').strip()
            if candidate and has_quota_headroom(candidate, needs_receipt=needs_receipt):
                donors.append(candidate)
        return donors
    except Exception:
        logger.exception('list_eligible_donors failed tenant=%s', tenant.tenant_id)
        raise


def count_sender_messages_in_window(sender_line_user_id: str, *, window_seconds: int) -> int:
    if not is_usage_tracking_enabled():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    try:
        client = get_supabase_client()
        resp = (
            client.table('llm_message_windows')
            .select('id', count='exact')
            .eq('sender_line_user_id', sender_line_user_id)
            .gte('created_at', cutoff.isoformat())
            .execute()
        )
        return int(resp.count or 0)
    except Exception:
        logger.exception('count_sender_messages_in_window failed user=%s', sender_line_user_id)
        raise


def record_llm_backed_message(sender_line_user_id: str, source_message_id: str) -> bool:
    """Insert message window row. Returns True if inserted, False if duplicate."""
    if not is_usage_tracking_enabled() or not source_message_id:
        return False
    try:
        client = get_supabase_client()
        client.table('llm_message_windows').insert(
            {
                'sender_line_user_id': sender_line_user_id,
                'source_message_id': source_message_id,
            }
        ).execute()
        return True
    except Exception as exc:
        message = str(exc).lower()
        if 'duplicate' in message or 'unique' in message or '23505' in message:
            return False
        logger.exception('record_llm_backed_message failed user=%s', sender_line_user_id)
        raise


def record_llm_usage(
    *,
    charged_line_user_id: str,
    sender_line_user_id: str,
    operation_type: str,
    operation_label: str,
    source_message_id: Optional[str],
    tenant_type: Optional[str],
    tenant_id: Optional[str],
    pooled: bool,
) -> bool:
    """Persist usage event and bump counters. Returns False if idempotent duplicate."""
    if not is_usage_tracking_enabled():
        return True

    if source_message_id:
        try:
            client = get_supabase_client()
            existing = (
                client.table('llm_usage_events')
                .select('id')
                .eq('source_message_id', source_message_id)
                .eq('operation_label', operation_label)
                .limit(1)
                .execute()
            )
            if existing.data:
                return False
        except Exception:
            logger.exception('record_llm_usage idempotency check failed')
            raise

    is_receipt = operation_type == 'receipt_analysis'
    month = current_jst_year_month()
    limits = get_free_tier_limits()

    try:
        client = get_supabase_client()
        client.table('llm_usage_events').insert(
            {
                'id': str(uuid.uuid4()),
                'charged_line_user_id': charged_line_user_id,
                'sender_line_user_id': sender_line_user_id,
                'operation_type': operation_type,
                'operation_label': operation_label,
                'source_message_id': source_message_id,
                'tenant_type': tenant_type,
                'tenant_id': tenant_id,
                'pooled': pooled,
            }
        ).execute()

        snap = get_user_usage_snapshot(charged_line_user_id)
        if snap.month_invocations >= limits.monthly_total:
            logger.warning('record_llm_usage over monthly total for user=%s', charged_line_user_id)
        new_month_total = snap.month_invocations + 1
        new_receipt_total = snap.month_receipt_analyses + (1 if is_receipt else 0)
        new_lifetime = snap.lifetime_invocations + 1

        client.table('user_usage_summary').upsert(
            {
                'line_user_id': charged_line_user_id,
                'jst_year_month': month,
                'tier': limits.tier,
                'lifetime_invocations': 0,
                'month_invocations': new_month_total,
                'month_receipt_analyses': new_receipt_total,
            },
            on_conflict='line_user_id,jst_year_month',
        ).execute()

        client.table('user_usage_summary').upsert(
            {
                'line_user_id': charged_line_user_id,
                'jst_year_month': LIFETIME_BUCKET,
                'tier': limits.tier,
                'lifetime_invocations': new_lifetime,
                'month_invocations': 0,
                'month_receipt_analyses': 0,
            },
            on_conflict='line_user_id,jst_year_month',
        ).execute()
        return True
    except Exception as exc:
        message = str(exc).lower()
        if source_message_id and ('duplicate' in message or 'unique' in message or '23505' in message):
            return False
        logger.exception('record_llm_usage failed user=%s', charged_line_user_id)
        raise
