"""Budget comparison snapshot for monthly report charts."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from services.budget_pace import (
    BudgetLevel,
    compute_budget_health,
    fetch_budget_summary,
)
from services.monthly_report_period import ReportPeriod
from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)

MAX_WORST_VARIANCE = 3


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal('0')


def _category_name(client: Any, node_id: Optional[str]) -> str:
    if not node_id:
        return 'Category'
    try:
        response = (
            client.table('category_nodes')
            .select('name_ja, name_en, code')
            .eq('id', node_id)
            .maybe_single()
            .execute()
        )
        row = response.data or {}
        return str(row.get('name_ja') or row.get('name_en') or row.get('code') or node_id)
    except Exception:
        return str(node_id)


def _bucket_key(level: str, category_node_id: Optional[str]) -> str:
    if level == 'total':
        return 'total'
    return f'{level}:{category_node_id}'


def _pace_ratio(spent: Decimal, limit: Decimal, elapsed: int, days: int) -> Optional[float]:
    if limit <= 0 or days <= 0:
        return None
    health = compute_budget_health(
        spent=float(spent),
        limit=float(limit),
        elapsed_days=max(1, elapsed),
        days_in_month=days,
    )
    return float(health.pace_ratio) if health.pace_ratio is not None else None


def build_budget_snapshot(
    tenant: TenantContext,
    period: ReportPeriod,
    currency: str = 'JPY',
) -> Dict[str, Any]:
    """Build snapshot_json: total + ≤3 worst-variance categories."""
    summary = fetch_budget_summary(tenant, period.period_start, currency=currency)
    if not summary or not summary.get('has_any_limit'):
        return _spending_fallback_snapshot(tenant, period, currency)

    budgets = summary.get('budgets') or []
    spent_by_bucket = summary.get('spent_by_bucket') or {}
    elapsed = int(summary.get('elapsed_days') or 1)
    days = int(summary.get('days_in_month') or 30)

    total_row = next((b for b in budgets if b.get('budget_level') == 'total'), None)
    total_payload = None
    if total_row:
        limit = _dec(total_row.get('amount'))
        spent = _dec(spent_by_bucket.get('total', 0))
        total_payload = {
            'limit': float(limit),
            'spent': float(spent),
            'remaining': float(limit - spent),
            'pace_ratio': _pace_ratio(spent, limit, elapsed, days),
        }

    category_candidates: List[Dict[str, Any]] = []
    client = get_supabase_client() if is_supabase_configured() else None
    for row in budgets:
        level = str(row.get('budget_level') or '')
        if level not in ('l1', 'l2'):
            continue
        node_id = row.get('category_node_id')
        limit = _dec(row.get('amount'))
        spent = _dec(spent_by_bucket.get(_bucket_key(level, node_id), 0))
        overshoot = spent - limit
        pace = _pace_ratio(spent, limit, elapsed, days)
        name = _category_name(client, str(node_id) if node_id else None) if client else str(node_id)
        category_candidates.append(
            {
                'category_node_id': str(node_id) if node_id else None,
                'name': name,
                'level': level,
                'limit': float(limit),
                'spent': float(spent),
                'remaining': float(limit - spent),
                'pace_ratio': pace,
                'overshoot': float(overshoot),
                'ahead': bool(pace is not None and pace > 1),
            }
        )

    category_candidates.sort(
        key=lambda c: (
            0 if c['overshoot'] > 0 else 1,
            -c['overshoot'] if c['overshoot'] > 0 else 0,
            0 if c['ahead'] else 1,
            -(c['pace_ratio'] or 0) if c['ahead'] else 0,
            c['category_node_id'] or '',
        )
    )
    selected = category_candidates[:MAX_WORST_VARIANCE]
    for idx, item in enumerate(selected, start=1):
        item['variance_rank'] = idx
        item.pop('overshoot', None)
        item.pop('ahead', None)

    top_spend = _top_spend_category(category_candidates) or (
        selected[0]
        if selected
        else None
    )
    severity = _overspend_severity(total_payload, selected)

    return {
        'has_any_budget': True,
        'total': total_payload,
        'categories': selected,
        'top_spend_category': (
            {'id': top_spend.get('category_node_id'), 'name': top_spend.get('name')}
            if top_spend
            else None
        ),
        'overspend_severity': severity,
        'period_start': period.period_start.isoformat(),
        'period_end': period.period_end.isoformat(),
    }


def _top_spend_category(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None
    return max(candidates, key=lambda c: (c.get('spent') or 0, c.get('category_node_id') or ''))


def _overspend_severity(total: Optional[Dict[str, Any]], categories: List[Dict[str, Any]]) -> str:
    if total and total.get('spent', 0) > total.get('limit', 0):
        return 'high'
    if any((c.get('spent') or 0) > (c.get('limit') or 0) for c in categories):
        return 'caution'
    if total and (total.get('pace_ratio') or 0) > 1.15:
        return 'caution'
    if any((c.get('pace_ratio') or 0) > 1.15 for c in categories):
        return 'caution'
    return 'none'


def _spending_fallback_snapshot(
    tenant: TenantContext,
    period: ReportPeriod,
    currency: str,
) -> Dict[str, Any]:
    """No applicable budget: spending summary only."""
    spent_total = 0.0
    top = None
    if is_supabase_configured():
        try:
            client = get_supabase_client()
            response = (
                client.table('expenses')
                .select('amount, category_l1_id, category_l2_id')
                .eq('tenant_type', tenant.tenant_type)
                .eq('tenant_id', tenant.tenant_id)
                .eq('currency', currency.upper()[:3])
                .gte('expense_date', period.period_start.isoformat())
                .lte('expense_date', period.period_end.isoformat())
                .is_('deleted_at', 'null')
                .execute()
            )
            rows = response.data or []
            by_cat: Dict[str, float] = {}
            for row in rows:
                amount = float(row.get('amount') or 0)
                spent_total += amount
                cat = row.get('category_l2_id') or row.get('category_l1_id') or 'other'
                by_cat[str(cat)] = by_cat.get(str(cat), 0.0) + amount
            if by_cat:
                cat_id = max(by_cat.items(), key=lambda kv: (kv[1], kv[0]))[0]
                top = {'id': cat_id, 'name': _category_name(client, cat_id)}
        except Exception:
            logger.exception('spending fallback snapshot failed')

    return {
        'has_any_budget': False,
        'total': None,
        'categories': [],
        'spending_total': spent_total,
        'top_spend_category': top,
        'overspend_severity': 'none',
        'period_start': period.period_start.isoformat(),
        'period_end': period.period_end.isoformat(),
    }
