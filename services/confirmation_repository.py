from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from services.message_context import ConfirmationItemSnapshot
from services.tenant_context import TenantContext
from services.supabase_client import get_supabase_client, is_supabase_configured

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfirmationRecord:
    id: str
    bot_message_id: str
    tenant: TenantContext
    confirmation_text: str
    items_snapshot: tuple[Dict[str, Any], ...]
    pending_action: Optional[str]

    @property
    def line_user_id(self) -> str:
        return self.tenant.logged_by_line_user_id


def _snapshot_to_json(items: List[ConfirmationItemSnapshot]) -> List[Dict[str, Any]]:
    return [
        {
            'line_item_index': item.line_item_index,
            'expense_id': item.expense_id,
            'description': item.description,
            'amount': float(item.amount),
            'currency': item.currency,
            'category_guess_code': item.category_guess_code,
            'category_alternatives': list(item.category_alternatives),
        }
        for item in items
    ]


def save_confirmation(
    bot_message_id: str,
    tenant: TenantContext,
    confirmation_text: str,
    items: List[ConfirmationItemSnapshot],
) -> Optional[str]:
    if not is_supabase_configured() or not items:
        logger.warning('Skipping confirmation save (configured=%s items=%d)', is_supabase_configured(), len(items))
        return None

    confirmation_id = str(uuid.uuid4())
    try:
        client = get_supabase_client()
        row = {
            'id': confirmation_id,
            'bot_message_id': bot_message_id,
            'interaction_bot_message_id': bot_message_id,
            'tenant_type': tenant.tenant_type,
            'tenant_id': tenant.tenant_id,
            'line_user_id': tenant.logged_by_line_user_id,
            'confirmation_text': confirmation_text,
            'items_snapshot': _snapshot_to_json(items),
            'pending_action': None,
        }
        client.table('confirmation_messages').insert(row).execute()

        links = [
            {
                'confirmation_id': confirmation_id,
                'expense_id': item.expense_id,
                'line_item_index': item.line_item_index,
            }
            for item in items
        ]
        if links:
            client.table('confirmation_expenses').insert(links).execute()

        logger.info('Saved confirmation bot_message_id=%s items=%d', bot_message_id, len(items))
        return confirmation_id
    except Exception:
        logger.exception('save_confirmation failed')
        return None


def get_confirmation_by_bot_message_id(
    bot_message_id: str,
    tenant: TenantContext,
) -> Optional[ConfirmationRecord]:
    if not is_supabase_configured():
        return None

    try:
        client = get_supabase_client()
        response = (
            client.table('confirmation_messages')
            .select('*')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .or_(
                f'bot_message_id.eq.{bot_message_id},interaction_bot_message_id.eq.{bot_message_id}'
            )
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        row = rows[0]
        snapshot = row.get('items_snapshot') or []
        record_tenant = TenantContext(
            tenant_type=str(row.get('tenant_type') or tenant.tenant_type),
            tenant_id=str(row.get('tenant_id') or tenant.tenant_id),
            logged_by_line_user_id=str(row.get('line_user_id') or tenant.logged_by_line_user_id),
        )
        return ConfirmationRecord(
            id=row['id'],
            bot_message_id=row['bot_message_id'],
            tenant=record_tenant,
            confirmation_text=row.get('confirmation_text') or '',
            items_snapshot=tuple(snapshot),
            pending_action=row.get('pending_action'),
        )
    except Exception:
        logger.exception('get_confirmation_by_bot_message_id failed')
        return None


def update_items_snapshot(confirmation_id: str, items_snapshot: List[Dict[str, Any]]) -> bool:
    if not is_supabase_configured():
        return False
    try:
        client = get_supabase_client()
        client.table('confirmation_messages').update({'items_snapshot': items_snapshot}).eq('id', confirmation_id).execute()
        return True
    except Exception:
        logger.exception('update_items_snapshot failed')
        return False


def update_interaction_bot_message_id(confirmation_id: str, bot_message_id: str) -> bool:
    if not is_supabase_configured() or not bot_message_id:
        return False
    try:
        client = get_supabase_client()
        client.table('confirmation_messages').update(
            {'interaction_bot_message_id': bot_message_id}
        ).eq('id', confirmation_id).execute()
        logger.info(
            'Updated interaction anchor confirmation_id=%s message_id=%s',
            confirmation_id,
            bot_message_id,
        )
        return True
    except Exception:
        logger.exception('update_interaction_bot_message_id failed')
        return False


def set_pending_action(confirmation_id: str, action: Optional[str]) -> bool:
    if not is_supabase_configured():
        return False
    try:
        client = get_supabase_client()
        client.table('confirmation_messages').update({'pending_action': action}).eq('id', confirmation_id).execute()
        return True
    except Exception:
        logger.exception('set_pending_action failed')
        return False


def try_mark_reply_processed(tenant: TenantContext, user_reply_message_id: str) -> bool:
    """Return True if this reply may be processed; False if duplicate."""
    if not is_supabase_configured():
        return True

    try:
        client = get_supabase_client()
        existing = (
            client.table('processed_reply_messages')
            .select('user_reply_message_id')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .eq('user_reply_message_id', user_reply_message_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            return False

        client.table('processed_reply_messages').insert(
            {
                'tenant_type': tenant.tenant_type,
                'tenant_id': tenant.tenant_id,
                'line_user_id': tenant.logged_by_line_user_id,
                'user_reply_message_id': user_reply_message_id,
            }
        ).execute()
        return True
    except Exception:
        logger.exception('try_mark_reply_processed failed')
        return True


def write_audit(
    confirmation_id: str,
    line_user_id: str,
    user_reply_message_id: str,
    user_reply_text: str,
    intent_json: Dict[str, Any],
    result_status: str,
    result_summary: str,
) -> None:
    if not is_supabase_configured():
        return
    try:
        client = get_supabase_client()
        client.table('reply_edit_audit').insert(
            {
                'confirmation_id': confirmation_id,
                'line_user_id': line_user_id,
                'user_reply_message_id': user_reply_message_id,
                'user_reply_text': user_reply_text,
                'intent_json': intent_json,
                'result_status': result_status,
                'result_summary': result_summary,
            }
        ).execute()
    except Exception:
        logger.exception('write_audit failed')
