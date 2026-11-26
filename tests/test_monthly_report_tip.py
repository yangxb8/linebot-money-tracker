"""Unit tests for new-period tip once-per-conversation."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from services.monthly_report import maybe_new_period_tip
from services.monthly_report_repository import clear_memory_store, tip_already_shown
from services.tenant_context import TenantContext


@pytest.fixture(autouse=True)
def _clear():
    clear_memory_store()
    yield
    clear_memory_store()


def test_tip_once_then_skip():
    tenant = TenantContext.personal('U-tip')
    with patch(
        'services.monthly_report.fetch_fiscal_start_day', return_value=1
    ), patch(
        'services.monthly_report.today_jst', return_value=date(2026, 11, 5)
    ), patch(
        'services.monthly_report_repository.is_supabase_configured', return_value=False
    ):
        first = maybe_new_period_tip(tenant, 'en')
        second = maybe_new_period_tip(tenant, 'en')

    assert first is not None
    assert 'report' in first.lower() or 'レポート' in first
    assert second is None
    assert tip_already_shown(tenant, date(2026, 11, 1))


def test_group_tip_once_for_conversation():
    group = TenantContext.group('G-tip', 'U-member')
    with patch(
        'services.monthly_report.fetch_fiscal_start_day', return_value=1
    ), patch(
        'services.monthly_report.today_jst', return_value=date(2026, 11, 5)
    ), patch(
        'services.monthly_report_repository.is_supabase_configured', return_value=False
    ):
        first = maybe_new_period_tip(group, 'ja')
        again = maybe_new_period_tip(group, 'ja')

    assert first is not None
    assert again is None
