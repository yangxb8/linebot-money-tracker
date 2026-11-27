"""Fiscal period resolution for monthly expense reports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from services.budget_pace import (
    _fetch_fiscal_start_day,
    fiscal_period_end,
    fiscal_period_start_for_date,
)
from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

JST = ZoneInfo('Asia/Tokyo')

_MONTH_NAME_EN = {
    'january': 1,
    'jan': 1,
    'february': 2,
    'feb': 2,
    'march': 3,
    'mar': 3,
    'april': 4,
    'apr': 4,
    'may': 5,
    'june': 6,
    'jun': 6,
    'july': 7,
    'jul': 7,
    'august': 8,
    'aug': 8,
    'september': 9,
    'sep': 9,
    'sept': 9,
    'october': 10,
    'oct': 10,
    'november': 11,
    'nov': 11,
    'december': 12,
    'dec': 12,
}


@dataclass(frozen=True)
class ReportPeriod:
    period_start: date
    period_end: date
    fiscal_start_day: int
    label: str


@dataclass(frozen=True)
class PeriodResolveError:
    code: str  # future | invalid


def today_jst() -> date:
    return datetime.now(JST).date()


def fetch_fiscal_start_day(tenant: TenantContext) -> int:
    if not is_supabase_configured():
        return 1
    try:
        return _fetch_fiscal_start_day(get_supabase_client(), tenant)
    except Exception:
        return 1


def previous_completed_period(as_of: date, fiscal_start_day: int) -> tuple[date, date]:
    current_start = fiscal_period_start_for_date(as_of, fiscal_start_day)
    prev_end = current_start - timedelta(days=1)
    prev_start = fiscal_period_start_for_date(prev_end, fiscal_start_day)
    return prev_start, fiscal_period_end(prev_start)


def current_period(as_of: date, fiscal_start_day: int) -> tuple[date, date]:
    start = fiscal_period_start_for_date(as_of, fiscal_start_day)
    return start, fiscal_period_end(start)


def _label_for(period_start: date, period_end: date, language: str = 'en') -> str:
    if language.startswith('ja'):
        return f'{period_start.year}年{period_start.month}月期（{period_start.isoformat()}〜{period_end.isoformat()}）'
    if language.startswith('zh'):
        return f'{period_start.year}年{period_start.month}月（{period_start.isoformat()}–{period_end.isoformat()}）'
    return f'{period_start.strftime("%b %Y")} ({period_start.isoformat()}–{period_end.isoformat()})'


def resolve_report_period(
    tenant: TenantContext,
    user_text: str,
    *,
    as_of: Optional[date] = None,
    language: str = 'ja',
) -> ReportPeriod | PeriodResolveError:
    """Default = previous completed fiscal period; honor named current/past."""
    as_of = as_of or today_jst()
    fiscal_start_day = fetch_fiscal_start_day(tenant)
    text = (user_text or '').strip().lower()

    want_current = bool(
        re.search(
            r'(this\s+month|current\s+(?:month|period)|今月|本月|这个月|這個月)',
            text,
            re.IGNORECASE,
        )
    )
    want_last = bool(
        re.search(r'(last\s+month|previous\s+month|先月|上个月|上個月)', text, re.IGNORECASE)
    )

    named_month: Optional[int] = None
    for name, month in _MONTH_NAME_EN.items():
        if re.search(rf'\b{name}\b', text):
            named_month = month
            break
    jp_month = re.search(r'(\d{1,2})\s*月', user_text or '')
    if jp_month:
        named_month = int(jp_month.group(1))

    year_match = re.search(r'(20\d{2})', text)
    named_year = int(year_match.group(1)) if year_match else as_of.year

    if named_month is not None:
        if named_month < 1 or named_month > 12:
            return PeriodResolveError(code='invalid')
        # Map calendar month name to the fiscal period that contains that calendar month's typical day
        probe = date(named_year, named_month, min(fiscal_start_day, 28))
        start = fiscal_period_start_for_date(probe, fiscal_start_day)
        end = fiscal_period_end(start)
        if start > fiscal_period_start_for_date(as_of, fiscal_start_day):
            return PeriodResolveError(code='future')
        return ReportPeriod(
            period_start=start,
            period_end=end,
            fiscal_start_day=fiscal_start_day,
            label=_label_for(start, end, language),
        )

    if want_current and not want_last:
        start, end = current_period(as_of, fiscal_start_day)
        return ReportPeriod(
            period_start=start,
            period_end=end,
            fiscal_start_day=fiscal_start_day,
            label=_label_for(start, end, language),
        )

    start, end = previous_completed_period(as_of, fiscal_start_day)
    return ReportPeriod(
        period_start=start,
        period_end=end,
        fiscal_start_day=fiscal_start_day,
        label=_label_for(start, end, language),
    )
