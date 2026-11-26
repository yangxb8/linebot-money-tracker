"""Unit tests for monthly report fiscal period resolution."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from services.monthly_report_period import (
    PeriodResolveError,
    current_period,
    previous_completed_period,
    resolve_report_period,
)
from services.tenant_context import TenantContext


def _tenant() -> TenantContext:
    return TenantContext.personal('U-test-period')


def test_previous_completed_start_day_1():
    start, end = previous_completed_period(date(2026, 11, 27), 1)
    assert start == date(2026, 10, 1)
    assert end == date(2026, 10, 31)


def test_previous_completed_non_1_start():
    # Fiscal months start on the 25th; as_of Nov 27 → current Nov 25–Dec 24 → previous Oct 25–Nov 24
    start, end = previous_completed_period(date(2026, 11, 27), 25)
    assert start == date(2026, 10, 25)
    assert end == date(2026, 11, 24)


def test_current_period_start_day_1():
    start, end = current_period(date(2026, 11, 27), 1)
    assert start == date(2026, 11, 1)
    assert end == date(2026, 11, 30)


def test_resolve_defaults_to_previous_completed():
    with patch('services.monthly_report_period.fetch_fiscal_start_day', return_value=1):
        period = resolve_report_period(
            _tenant(),
            'monthly report',
            as_of=date(2026, 11, 27),
            language='en',
        )
    assert not isinstance(period, PeriodResolveError)
    assert period.period_start == date(2026, 10, 1)
    assert period.period_end == date(2026, 10, 31)


def test_resolve_current_month_phrase():
    with patch('services.monthly_report_period.fetch_fiscal_start_day', return_value=1):
        period = resolve_report_period(
            _tenant(),
            "this month's report",
            as_of=date(2026, 11, 27),
            language='en',
        )
    assert not isinstance(period, PeriodResolveError)
    assert period.period_start == date(2026, 11, 1)


def test_resolve_future_named_month_rejected():
    with patch('services.monthly_report_period.fetch_fiscal_start_day', return_value=1):
        result = resolve_report_period(
            _tenant(),
            'December 2099 report',
            as_of=date(2026, 11, 27),
            language='en',
        )
    assert isinstance(result, PeriodResolveError)
    assert result.code == 'future'
