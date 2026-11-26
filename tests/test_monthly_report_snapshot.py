"""Unit tests for budget comparison snapshot construction."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from services.monthly_report_period import ReportPeriod
from services.monthly_report_snapshot import (
    MAX_WORST_VARIANCE,
    build_budget_snapshot,
)
from services.tenant_context import TenantContext


def _period() -> ReportPeriod:
    return ReportPeriod(
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        fiscal_start_day=1,
        label='Oct 2026',
    )


def test_includes_total_and_worst_variance_ranking():
    summary = {
        'has_any_limit': True,
        'elapsed_days': 20,
        'days_in_month': 31,
        'budgets': [
            {'budget_level': 'total', 'category_node_id': None, 'amount': 100000},
            {'budget_level': 'l1', 'category_node_id': 'food', 'amount': 30000},
            {'budget_level': 'l1', 'category_node_id': 'transport', 'amount': 10000},
            {'budget_level': 'l1', 'category_node_id': 'fun', 'amount': 5000},
            {'budget_level': 'l1', 'category_node_id': 'housing', 'amount': 40000},
        ],
        'spent_by_bucket': {
            'total': 95000,
            'l1:food': 45000,  # over by 15k
            'l1:transport': 12000,  # over by 2k
            'l1:fun': 8000,  # over by 3k
            'l1:housing': 30000,  # under
        },
    }
    with patch(
        'services.monthly_report_snapshot.fetch_budget_summary', return_value=summary
    ), patch(
        'services.monthly_report_snapshot.is_supabase_configured', return_value=False
    ):
        snap = build_budget_snapshot(TenantContext.personal('U1'), _period())

    assert snap['has_any_budget'] is True
    assert snap['total']['spent'] == 95000
    assert snap['total']['limit'] == 100000
    cats = snap['categories']
    assert len(cats) <= MAX_WORST_VARIANCE
    assert cats[0]['category_node_id'] == 'food'
    assert [c['variance_rank'] for c in cats] == list(range(1, len(cats) + 1))


def test_no_budget_fallback():
    with patch(
        'services.monthly_report_snapshot.fetch_budget_summary',
        return_value={'has_any_limit': False, 'budgets': []},
    ), patch(
        'services.monthly_report_snapshot.is_supabase_configured', return_value=False
    ):
        snap = build_budget_snapshot(TenantContext.personal('U1'), _period())

    assert snap['has_any_budget'] is False
    assert snap['total'] is None
    assert snap['categories'] == []
    assert 'spending_total' in snap
    assert snap['overspend_severity'] == 'none'


def test_overspend_severity_high_when_total_over():
    summary = {
        'has_any_limit': True,
        'elapsed_days': 10,
        'days_in_month': 31,
        'budgets': [
            {'budget_level': 'total', 'category_node_id': None, 'amount': 50000},
        ],
        'spent_by_bucket': {'total': 60000},
    }
    with patch(
        'services.monthly_report_snapshot.fetch_budget_summary', return_value=summary
    ), patch(
        'services.monthly_report_snapshot.is_supabase_configured', return_value=False
    ):
        snap = build_budget_snapshot(TenantContext.personal('U1'), _period())
    assert snap['overspend_severity'] == 'high'
