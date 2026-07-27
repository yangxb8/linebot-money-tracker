"""Wish list repository and bot reply helpers (feature 020)."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from services.message_context import BotReply, ConfirmationSavePayload, MessageContext
from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext
from services.tenant_settings import resolve_tenant_reply_language
from services.wish_list_budget import WishBudgetImpact, build_wish_list_budget_impact

logger = logging.getLogger(__name__)

_WISH_PHRASE_RE = re.compile(
    r'(i\s+want\s+to\s+buy|want\s+to\s+buy|wishlist|wish\s+list|'
    r'買いたい|ほしい|欲しい|まだ買ってない|まだ買っていない|'
    r'想买|想買|想要买|还没买|還沒買)',
    re.IGNORECASE,
)

_URL_RE = re.compile(r'https?://[^\s]+', re.IGNORECASE)


@dataclass(frozen=True)
class WishListCandidate:
    name: str
    amount: Decimal
    currency: str
    assigned_level: int
    category_node_id: str
    category_l1_id: str
    category_l2_id: Optional[str]
    category_l3_id: Optional[str]
    category_label: str
    product_url: Optional[str]


def looks_like_wish_list_intent(text: Optional[str]) -> bool:
    if not text or not isinstance(text, str):
        return False
    return bool(_WISH_PHRASE_RE.search(text.strip()))


def extract_product_url(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    match = _URL_RE.search(text)
    if not match:
        return None
    url = match.group(0).rstrip('.,)〉」』')
    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https') and parsed.netloc:
        return url
    return None


def next_sort_order(tenant: TenantContext) -> int:
    if not is_supabase_configured():
        return 0
    try:
        client = get_supabase_client()
        response = (
            client.table('wish_list_items')
            .select('sort_order')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .eq('status', 'active')
            .is_('deleted_at', 'null')
            .order('sort_order', desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return 0
        return int(rows[0].get('sort_order') or 0) + 1
    except Exception:
        logger.exception('next_sort_order failed')
        return 0


def insert_active_wish_list_item(
    tenant: TenantContext,
    *,
    name: str,
    amount: Decimal | float | int | str,
    assigned_level: int,
    category_node_id: str,
    category_l1_id: str,
    category_l2_id: Optional[str] = None,
    category_l3_id: Optional[str] = None,
    product_url: Optional[str] = None,
    currency: str = 'JPY',
    created_by_line_user_id: Optional[str] = None,
) -> Optional[str]:
    if not is_supabase_configured():
        logger.warning('insert_active_wish_list_item skipped (supabase not configured)')
        return None

    amount_dec = Decimal(str(amount)).quantize(Decimal('0.01'))
    if amount_dec <= 0:
        logger.warning('insert_active_wish_list_item rejected non-positive amount')
        return None

    row = {
        'id': str(uuid.uuid4()),
        'tenant_type': tenant.tenant_type,
        'tenant_id': tenant.tenant_id,
        'name': name.strip(),
        'amount': float(amount_dec),
        'currency': (currency or 'JPY').strip().upper()[:3],
        'assigned_level': assigned_level,
        'category_node_id': category_node_id,
        'category_l1_id': category_l1_id,
        'category_l2_id': category_l2_id,
        'category_l3_id': category_l3_id,
        'product_url': product_url,
        'sort_order': next_sort_order(tenant),
        'status': 'active',
        'executed_expense_id': None,
        'created_by_line_user_id': created_by_line_user_id or tenant.logged_by_line_user_id,
    }
    try:
        client = get_supabase_client()
        client.table('wish_list_items').insert(row).execute()
        logger.info(
            'Inserted wish_list_item id=%s tenant=%s:%s',
            row['id'],
            tenant.tenant_type,
            tenant.tenant_id,
        )
        return row['id']
    except Exception:
        logger.exception('insert_active_wish_list_item failed')
        return None


def format_wish_budget_impact_lines(impact: WishBudgetImpact, language: str) -> List[str]:
    if not impact.has_budget:
        if language == 'en':
            return ['No budget limit is set for this purchase.']
        if language == 'zh':
            return ['此购买没有适用的预算上限。']
        return ['この購入に適用される予算上限はありません。']

    label = impact.label or ''
    remaining_now = int(impact.remaining_now or 0)
    remaining_if = int(impact.remaining_if_purchased or 0)
    if language == 'en':
        lines = [
            f'Budget ({label}): ¥{remaining_now:,} left now → ¥{remaining_if:,} if you buy this.',
        ]
        if impact.is_ahead_if_purchased:
            daily = int(impact.daily_allowance_if_purchased or 0)
            days = int(impact.days_remaining or 0)
            lines.append(
                f'⚠️ This would put spending ahead of pace '
                f'(~¥{daily:,}/day for {days} days left).'
            )
        return lines

    if language == 'zh':
        lines = [
            f'预算（{label}）：现在剩余 ¥{remaining_now:,} → 购买后剩余 ¥{remaining_if:,}。',
        ]
        if impact.is_ahead_if_purchased:
            daily = int(impact.daily_allowance_if_purchased or 0)
            days = int(impact.days_remaining or 0)
            lines.append(f'⚠️ 购买后支出节奏会偏快（剩余 {days} 天约 ¥{daily:,}/天）。')
        return lines

    lines = [
        f'予算（{label}）：残り ¥{remaining_now:,} → 買うと ¥{remaining_if:,}。',
    ]
    if impact.is_ahead_if_purchased:
        daily = int(impact.daily_allowance_if_purchased or 0)
        days = int(impact.days_remaining or 0)
        lines.append(f'⚠️ 買うとペース超過になります（残り{days}日で約¥{daily:,}/日）。')
    return lines


def format_wish_list_proposal(
    candidate: WishListCandidate,
    impact: WishBudgetImpact,
    language: str,
) -> str:
    amount = int(candidate.amount)
    if language == 'en':
        lines = [
            'Wishlist candidate (not logged as an expense):',
            f'• {candidate.name} — ¥{amount:,} / {candidate.category_label}',
        ]
        if candidate.product_url:
            lines.append(f'Link: {candidate.product_url}')
        lines.extend(format_wish_budget_impact_lines(impact, language))
        lines.append('Add to wishlist? Reply yes / no')
        return '\n'.join(lines)

    if language == 'zh':
        lines = [
            '愿望单候选项（未记为支出）：',
            f'• {candidate.name} — ¥{amount:,} / {candidate.category_label}',
        ]
        if candidate.product_url:
            lines.append(f'链接：{candidate.product_url}')
        lines.extend(format_wish_budget_impact_lines(impact, language))
        lines.append('要加入愿望单吗？请回复 yes / no（或 是 / 不用）')
        return '\n'.join(lines)

    lines = [
        'ウィッシュリスト候補（支出には記録していません）：',
        f'• {candidate.name} — ¥{amount:,} / {candidate.category_label}',
    ]
    if candidate.product_url:
        lines.append(f'リンク: {candidate.product_url}')
    lines.extend(format_wish_budget_impact_lines(impact, language))
    lines.append('ウィッシュリストに追加しますか？ yes / no（はい / いいえ）で返信してください')
    return '\n'.join(lines)


def format_wish_list_need_price(language: str) -> str:
    """Legacy alias — prefer format_wish_list_ask_details for await-details prompts."""
    return format_wish_list_ask_details(language)


def format_wish_list_ask_details(language: str) -> str:
    if language == 'en':
        return (
            'I see you want to buy something. '
            'Reply to this message with the product name and price, '
            'or reply with a product photo.'
            '\n\n⏳ You have 30 seconds to send the product photo/image.'
        )
    if language == 'zh':
        return (
            '看起来你想买东西。'
            '请回复这条消息，发送商品名称和价格，'
            '或回复一张商品图片。'
            '\n\n⏳ 请在30秒内发送商品图片/照片。'
        )
    return (
        '買いたいものですね。'
        'このメッセージに返信して、商品名と金額を送るか、'
        '商品の写真を返信してください。'
        '\n\n⏳ この後30秒以内に商品画像/写真を送ってください。'
    )


def _reply_language(context: MessageContext) -> str:
    return resolve_tenant_reply_language(context.tenant, context.reply_language)


def build_wish_list_await_details_reply(context: MessageContext) -> BotReply:
    language = _reply_language(context)
    text = format_wish_list_ask_details(language)
    return BotReply(
        text=text,
        confirmation=ConfirmationSavePayload(
            tenant=context.tenant,
            confirmation_text=text,
            items=(),
            pending_action='wish_list_await_details',
            pending_payload={},
        ),
    )


def format_wish_list_added(language: str, name: str) -> str:
    if language == 'en':
        return f'Added to wishlist: {name}'
    if language == 'zh':
        return f'已加入愿望单：{name}'
    return f'ウィッシュリストに追加しました：{name}'


def format_wish_list_cancelled(language: str) -> str:
    if language == 'en':
        return 'Wishlist add cancelled.'
    if language == 'zh':
        return '已取消加入愿望单。'
    return 'ウィッシュリストへの追加をキャンセルしました。'


def candidate_to_pending_payload(candidate: WishListCandidate) -> Dict[str, Any]:
    return {
        'name': candidate.name,
        'amount': float(candidate.amount),
        'currency': candidate.currency,
        'assigned_level': candidate.assigned_level,
        'category_node_id': candidate.category_node_id,
        'category_l1_id': candidate.category_l1_id,
        'category_l2_id': candidate.category_l2_id,
        'category_l3_id': candidate.category_l3_id,
        'product_url': candidate.product_url,
        'category_label': candidate.category_label,
    }


def pending_payload_to_candidate(payload: Dict[str, Any]) -> Optional[WishListCandidate]:
    try:
        return WishListCandidate(
            name=str(payload['name']).strip(),
            amount=Decimal(str(payload['amount'])).quantize(Decimal('0.01')),
            currency=str(payload.get('currency') or 'JPY'),
            assigned_level=int(payload['assigned_level']),
            category_node_id=str(payload['category_node_id']),
            category_l1_id=str(payload['category_l1_id']),
            category_l2_id=payload.get('category_l2_id'),
            category_l3_id=payload.get('category_l3_id'),
            category_label=str(payload.get('category_label') or ''),
            product_url=payload.get('product_url'),
        )
    except (KeyError, TypeError, ValueError):
        logger.warning('Invalid wish_list pending payload: %s', payload)
        return None


def build_wish_list_proposal_reply(
    candidate: WishListCandidate,
    context: MessageContext,
) -> BotReply:
    language = _reply_language(context)
    impact = build_wish_list_budget_impact(
        context.tenant,
        float(candidate.amount),
        assigned_level=candidate.assigned_level,
        category_node_id=candidate.category_node_id,
        category_l1_id=candidate.category_l1_id,
        currency=candidate.currency,
        language=language,
    )
    text = format_wish_list_proposal(candidate, impact, language)
    return BotReply(
        text=text,
        confirmation=ConfirmationSavePayload(
            tenant=context.tenant,
            confirmation_text=text,
            items=(),
            pending_action='wish_list_add',
            pending_payload=candidate_to_pending_payload(candidate),
        ),
    )
