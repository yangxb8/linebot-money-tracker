"""Budget pace evaluation and LINE reply prepending."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Sequence
from zoneinfo import ZoneInfo

from services.budget_pace_i18n import format_pace_warning_template, total_budget_label
from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)

JST = ZoneInfo('Asia/Tokyo')
BudgetLevel = Literal['l2', 'l1', 'total']


@dataclass(frozen=True)
class HealthResult:
    spent_pct: Optional[float]
    time_pct: float
    pace_ratio: Optional[float]
    is_ahead: bool


@dataclass(frozen=True)
class BudgetLevelCandidate:
    level: BudgetLevel
    category_node_id: Optional[str]
    limit: Decimal
    spent: Decimal
    display_name: str


@dataclass(frozen=True)
class PaceWarning:
    level: BudgetLevel
    category_node_id: Optional[str]
    display_name: str
    daily_allowance: int
    remaining: Decimal
    days_remaining: int
    text: str
    source: Literal['llm', 'template'] = 'template'


def _warning_bucket_key(warning: PaceWarning, *, currency: str) -> tuple:
    return (warning.level, warning.category_node_id, currency)


def compute_budget_health(
    spent: float,
    limit: Optional[float],
    elapsed_days: int,
    days_in_month: int,
) -> HealthResult:
    time_pct = (
        min(1.0, max(0.0, elapsed_days / days_in_month))
        if days_in_month > 0
        else 0.0
    )

    if limit is None or limit <= 0:
        return HealthResult(spent_pct=None, time_pct=time_pct, pace_ratio=None, is_ahead=False)

    spent_pct = spent / limit

    if elapsed_days <= 1 or time_pct <= 0:
        return HealthResult(spent_pct=spent_pct, time_pct=time_pct, pace_ratio=None, is_ahead=False)

    pace_ratio = spent_pct / time_pct
    return HealthResult(
        spent_pct=spent_pct,
        time_pct=time_pct,
        pace_ratio=pace_ratio,
        is_ahead=pace_ratio > 1,
    )


def fiscal_period_start_for_date(expense_date: date, fiscal_start_day: int = 1) -> date:
    if expense_date.day >= fiscal_start_day:
        year, month = expense_date.year, expense_date.month
    elif expense_date.month == 1:
        year, month = expense_date.year - 1, 12
    else:
        year, month = expense_date.year, expense_date.month - 1
    return date(year, month, fiscal_start_day)


def fiscal_period_end(budget_month: date) -> date:
  from datetime import timedelta
  if budget_month.month == 12:
      next_start = date(budget_month.year + 1, 1, budget_month.day)
  else:
      next_start = date(budget_month.year, budget_month.month + 1, budget_month.day)
  return next_start - timedelta(days=1)


def _fetch_fiscal_start_day(client: Any, tenant: TenantContext) -> int:
    try:
        response = (
            client.table('tenant_settings')
            .select('fiscal_start_day')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .maybe_single()
            .execute()
        )
        if response.data and response.data.get('fiscal_start_day') is not None:
            return int(response.data['fiscal_start_day'])
    except Exception:
        logger.warning('fetch fiscal_start_day failed; defaulting to 1', exc_info=True)
    return 1


def _has_budget(budgets: Sequence[Dict[str, Any]], level: BudgetLevel, category_node_id: Optional[str]) -> bool:
    for row in budgets:
        if row.get('budget_level') != level:
            continue
        row_node = row.get('category_node_id')
        if level == 'total':
            if row_node is None:
                return True
        elif row_node == category_node_id:
            return True
    return False


def _limit_for(budgets: Sequence[Dict[str, Any]], level: BudgetLevel, category_node_id: Optional[str]) -> Optional[Decimal]:
    for row in budgets:
        if row.get('budget_level') != level:
            continue
        row_node = row.get('category_node_id')
        if level == 'total':
            if row_node is None:
                return Decimal(str(row['amount']))
        elif row_node == category_node_id:
            return Decimal(str(row['amount']))
    return None


def _bucket_spent(spent_by_bucket: Dict[str, Any], level: BudgetLevel, category_node_id: Optional[str]) -> Decimal:
    if level == 'total':
        key = 'total'
    else:
        key = f'{level}:{category_node_id}'
    value = spent_by_bucket.get(key, 0)
    return Decimal(str(value))


def build_level_candidates(
    expense_row: Dict[str, Any],
    budgets: Sequence[Dict[str, Any]],
    spent_by_bucket: Dict[str, Any],
    category_names: Dict[str, str],
    language: str,
) -> List[BudgetLevelCandidate]:
    assigned_level = int(expense_row['assigned_level'])
    category_node_id = str(expense_row['category_node_id'])
    category_l1_id = str(expense_row['category_l1_id'])
    candidates: List[BudgetLevelCandidate] = []

    if assigned_level == 2 and _has_budget(budgets, 'l2', category_node_id):
        limit = _limit_for(budgets, 'l2', category_node_id)
        if limit is not None:
            candidates.append(
                BudgetLevelCandidate(
                    level='l2',
                    category_node_id=category_node_id,
                    limit=limit,
                    spent=_bucket_spent(spent_by_bucket, 'l2', category_node_id),
                    display_name=category_names.get(category_node_id, category_node_id),
                )
            )

    l1_node_id = category_l1_id if assigned_level == 2 else category_node_id
    if _has_budget(budgets, 'l1', l1_node_id):
        limit = _limit_for(budgets, 'l1', l1_node_id)
        if limit is not None:
            candidates.append(
                BudgetLevelCandidate(
                    level='l1',
                    category_node_id=l1_node_id,
                    limit=limit,
                    spent=_bucket_spent(spent_by_bucket, 'l1', l1_node_id),
                    display_name=category_names.get(l1_node_id, l1_node_id),
                )
            )

    if _has_budget(budgets, 'total', None):
        limit = _limit_for(budgets, 'total', None)
        if limit is not None:
            candidates.append(
                BudgetLevelCandidate(
                    level='total',
                    category_node_id=None,
                    limit=limit,
                    spent=_bucket_spent(spent_by_bucket, 'total', None),
                    display_name=total_budget_label(language),
                )
            )

    return candidates


def find_lowest_ahead_warning(
    candidates: Sequence[BudgetLevelCandidate],
    *,
    elapsed_days: int,
    days_in_month: int,
    language: str,
) -> Optional[PaceWarning]:
    days_remaining = max(days_in_month - elapsed_days, 0)
    if days_remaining <= 0:
        return None

    for candidate in candidates:
        health = compute_budget_health(
            float(candidate.spent),
            float(candidate.limit),
            elapsed_days,
            days_in_month,
        )
        if not health.is_ahead:
            continue

        remaining = max(candidate.limit - candidate.spent, Decimal('0'))
        daily_allowance = (
            int(remaining // days_remaining) if days_remaining > 0 else 0
        )
        text = format_pace_warning_template(
            level=candidate.level,
            display_name=candidate.display_name,
            daily_allowance=daily_allowance,
            days_remaining=days_remaining,
            remaining=float(remaining),
            language=language,
        )
        return PaceWarning(
            level=candidate.level,
            category_node_id=candidate.category_node_id,
            display_name=candidate.display_name,
            daily_allowance=daily_allowance,
            remaining=remaining,
            days_remaining=days_remaining,
            text=text,
            source='template',
        )
    return None


def fetch_category_display_names(
    tenant: TenantContext,
    node_ids: Sequence[str],
) -> Dict[str, str]:
    if not node_ids or not is_supabase_configured():
        return {}
    try:
        client = get_supabase_client()
        response = (
            client.table('category_nodes')
            .select('id, name_ja, code')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .in_('id', list(set(node_ids)))
            .execute()
        )
        names: Dict[str, str] = {}
        for row in response.data or []:
            names[str(row['id'])] = str(row.get('name_ja') or row.get('code') or row['id'])
        return names
    except Exception:
        logger.warning('fetch_category_display_names failed', exc_info=True)
        return {}


def _resolve_spending_bucket(
    assigned_level: int,
    category_node_id: str,
    category_l1_id: str,
    budgets: Sequence[Dict[str, Any]],
) -> str:
    if assigned_level == 2 and _has_budget(budgets, 'l2', category_node_id):
        return f'l2:{category_node_id}'
    if _has_budget(budgets, 'l1', category_l1_id):
        return f'l1:{category_l1_id}'
    if _has_budget(budgets, 'total', None):
        return 'total'
    return 'unbudgeted'


def _build_spent_by_bucket(
    client: Any,
    tenant: TenantContext,
    budget_month: date,
    month_end: date,
    currency: str,
    budgets: Sequence[Dict[str, Any]],
) -> Dict[str, Decimal]:
    response = (
        client.table('expenses')
        .select('assigned_level, category_node_id, category_l1_id, amount')
        .eq('tenant_type', tenant.tenant_type)
        .eq('tenant_id', tenant.tenant_id)
        .eq('currency', currency)
        .is_('deleted_at', 'null')
        .gte('expense_date', budget_month.isoformat())
        .lte('expense_date', month_end.isoformat())
        .execute()
    )
    totals: Dict[str, Decimal] = {}
    for row in response.data or []:
        bucket = _resolve_spending_bucket(
            int(row['assigned_level']),
            str(row['category_node_id']),
            str(row['category_l1_id']),
            budgets,
        )
        if bucket == 'unbudgeted':
            continue
        amount = Decimal(str(row['amount']))
        totals[bucket] = totals.get(bucket, Decimal('0')) + amount
    return totals


def fetch_budget_summary(
    tenant: TenantContext,
    budget_month: date,
    currency: str = 'JPY',
) -> Optional[Dict[str, Any]]:
    if not is_supabase_configured():
        return None

    try:
        client = get_supabase_client()
        fiscal_start_day = _fetch_fiscal_start_day(client, tenant)
        month_end = fiscal_period_end(budget_month)
        days_in_month = (month_end - budget_month).days + 1

        today = datetime.now(JST).date()
        if today < budget_month:
            elapsed_days = 0
        elif today > month_end:
            elapsed_days = days_in_month
        else:
            elapsed_days = max(1, (today - budget_month).days + 1)

        budget_response = (
            client.table('monthly_budgets')
            .select('budget_level, category_node_id, amount')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .eq('budget_month', budget_month.isoformat())
            .eq('currency', currency.upper()[:3])
            .execute()
        )
        budgets = budget_response.data or []
        has_any_limit = len(budgets) > 0
        spent_by_bucket = _build_spent_by_bucket(
            client,
            tenant,
            budget_month,
            month_end,
            currency.upper()[:3],
            budgets,
        )

        return {
            'budget_month': budget_month.isoformat(),
            'fiscal_start_day': fiscal_start_day,
            'days_in_month': days_in_month,
            'elapsed_days': elapsed_days,
            'currency': currency.upper()[:3],
            'has_any_limit': has_any_limit,
            'budgets': budgets,
            'spent_by_bucket': {k: float(v) for k, v in spent_by_bucket.items()},
        }
    except Exception:
        logger.exception('fetch_budget_summary failed')
        return None


def _path_key(expense_row: Dict[str, Any]) -> tuple:
    expense_date = expense_row.get('expense_date')
    if isinstance(expense_date, str):
        expense_date = date.fromisoformat(expense_date[:10])
    elif not isinstance(expense_date, date):
        expense_date = datetime.now(JST).date()
    return (
        int(expense_row['assigned_level']),
        str(expense_row['category_node_id']),
        str(expense_row['category_l1_id']),
        expense_date.isoformat()[:7],
        str(expense_row.get('currency', 'JPY')).upper()[:3],
    )


def evaluate_pace_warnings(
    expense_rows: Sequence[Dict[str, Any]],
    tenant: TenantContext,
    *,
    language: str,
) -> List[PaceWarning]:
    if not expense_rows:
        return []

    unique_rows: Dict[tuple, Dict[str, Any]] = {}
    for row in expense_rows:
        unique_rows[_path_key(row)] = row

    warnings: List[PaceWarning] = []
    seen_buckets: set[tuple] = set()
    summaries: Dict[tuple, Dict[str, Any]] = {}

    for row in unique_rows.values():
        expense_date = row.get('expense_date')
        if isinstance(expense_date, str):
            expense_date = date.fromisoformat(expense_date[:10])
        elif not isinstance(expense_date, date):
            expense_date = datetime.now(JST).date()

        currency = str(row.get('currency', 'JPY')).upper()[:3]
        fiscal_start_day = 1
        if is_supabase_configured():
            try:
                fiscal_start_day = _fetch_fiscal_start_day(get_supabase_client(), tenant)
            except Exception:
                pass
        budget_month = fiscal_period_start_for_date(expense_date, fiscal_start_day)
        summary_key = (budget_month.isoformat(), currency)
        if summary_key not in summaries:
            summaries[summary_key] = fetch_budget_summary(tenant, budget_month, currency) or {}

        summary = summaries[summary_key]
        if not summary.get('has_any_limit'):
            continue

        node_ids = [str(row['category_node_id']), str(row['category_l1_id'])]
        category_names = fetch_category_display_names(tenant, node_ids)

        candidates = build_level_candidates(
            row,
            summary.get('budgets', []),
            summary.get('spent_by_bucket', {}),
            category_names,
            language,
        )
        warning = find_lowest_ahead_warning(
            candidates,
            elapsed_days=int(summary.get('elapsed_days', 0)),
            days_in_month=int(summary.get('days_in_month', 0)),
            language=language,
        )
        if warning is not None:
            bucket_key = _warning_bucket_key(warning, currency=currency)
            if bucket_key in seen_buckets:
                continue
            seen_buckets.add(bucket_key)
            warnings.append(warning)

    return warnings


def format_pace_warnings(warnings: Sequence[PaceWarning]) -> str:
    return '\n'.join(w.text for w in warnings)


async def _format_warnings_with_llm(
    warnings: Sequence[PaceWarning],
    *,
    language: str,
    gemini: Any,
) -> List[PaceWarning]:
    from services.budget_pace_prompt import build_budget_pace_prompt
    from services.usage_metering import llm_operation_scope

    formatted: List[PaceWarning] = []
    for warning in warnings:
        try:
            prompt = build_budget_pace_prompt(
                language=language,
                level=warning.level,
                display_name=warning.display_name,
                remaining=float(warning.remaining),
                days_remaining=warning.days_remaining,
                daily_allowance=warning.daily_allowance,
            )
            with llm_operation_scope('budget_pace'):
                text = (await gemini.generate_reply(prompt)).strip()
            if text:
                formatted.append(
                    PaceWarning(
                        level=warning.level,
                        category_node_id=warning.category_node_id,
                        display_name=warning.display_name,
                        daily_allowance=warning.daily_allowance,
                        remaining=warning.remaining,
                        days_remaining=warning.days_remaining,
                        text=text,
                        source='llm',
                    )
                )
            else:
                formatted.append(warning)
        except Exception:
            logger.warning('LLM budget pace warning failed; using template', exc_info=True)
            formatted.append(warning)
    return formatted


async def maybe_prepend_budget_pace_warning(
    body: str,
    *,
    expense_rows: Sequence[Dict[str, Any]],
    tenant: TenantContext,
    language: str,
    gemini: Any = None,
) -> str:
    if not body or not expense_rows:
        return body

    try:
        warnings = evaluate_pace_warnings(expense_rows, tenant, language=language)
        if not warnings:
            return body

        if gemini is not None:
            warnings = await _format_warnings_with_llm(warnings, language=language, gemini=gemini)

        warning_block = format_pace_warnings(warnings)
        if not warning_block:
            return body
        return f'{warning_block}\n\n{body}'
    except Exception:
        logger.exception('maybe_prepend_budget_pace_warning failed')
        return body


def expense_rows_from_enriched(
    items: Sequence[Dict[str, Any]],
    context: Any,
) -> List[Dict[str, Any]]:
    from services.category_taxonomy import resolve_code
    from services.expense_repository import expense_date_for_item

    rows: List[Dict[str, Any]] = []
    for item in items:
        code = item.get('category_guess_code')
        if not code:
            continue
        node = resolve_code(str(code), context.tenant)
        rows.append(
            {
                'assigned_level': node.level,
                'category_node_id': node.id,
                'category_l1_id': node.l1_id,
                'expense_date': expense_date_for_item(item),
                'currency': str(item.get('currency') or 'JPY').upper()[:3],
            }
        )
    return rows


def expense_row_from_insert_row(row: Any) -> Dict[str, Any]:
    return {
        'assigned_level': row.assigned_level,
        'category_node_id': row.category_node_id,
        'category_l1_id': row.category_l1_id,
        'expense_date': row.expense_date,
        'currency': row.currency,
    }


def expense_row_from_expense_row(row: Any) -> Dict[str, Any]:
    return {
        'assigned_level': row.assigned_level,
        'category_node_id': row.category_node_id,
        'category_l1_id': row.category_l1_id,
        'expense_date': row.expense_date,
        'currency': row.currency,
    }
