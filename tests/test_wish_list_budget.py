from datetime import date
from decimal import Decimal
from unittest.mock import patch

from services.budget_pace import BudgetLevelCandidate
from services.tenant_context import TenantContext
from services.wish_list_budget import build_wish_list_budget_impact


def test_budget_impact_remaining_when_on_pace():
    tenant = TenantContext.personal('user-1')
    summary = {
        'has_any_limit': True,
        'budget_month': '2026-07-01',
        'fiscal_start_day': 1,
        'elapsed_days': 10,
        'days_in_month': 30,
        'budgets': [{'budget_level': 'total', 'category_node_id': None, 'amount': 100000}],
        'spent_by_bucket': {'total': 20000},
    }
    candidate = BudgetLevelCandidate(
        level='total',
        category_node_id=None,
        limit=Decimal('100000'),
        spent=Decimal('20000'),
        display_name='Total',
    )
    with patch('services.wish_list_budget.fetch_budget_summary', return_value=summary), patch(
        'services.wish_list_budget.fetch_category_display_names',
        return_value={},
    ), patch(
        'services.wish_list_budget.find_applicable_budget_candidate',
        return_value=candidate,
    ):
        impact = build_wish_list_budget_impact(
            tenant,
            5000,
            assigned_level=1,
            category_node_id='c1',
            category_l1_id='c1',
        )

    assert impact.has_budget is True
    assert impact.remaining_now == 80000.0
    assert impact.remaining_if_purchased == 75000.0
    assert impact.is_ahead_if_purchased is False


def test_budget_impact_pace_when_ahead():
    tenant = TenantContext.personal('user-1')
    summary = {
        'has_any_limit': True,
        'budget_month': '2026-07-01',
        'fiscal_start_day': 1,
        'elapsed_days': 5,
        'days_in_month': 30,
        'budgets': [{'budget_level': 'total', 'category_node_id': None, 'amount': 30000}],
        'spent_by_bucket': {'total': 25000},
    }
    candidate = BudgetLevelCandidate(
        level='total',
        category_node_id=None,
        limit=Decimal('30000'),
        spent=Decimal('25000'),
        display_name='Total',
    )
    with patch('services.wish_list_budget.fetch_budget_summary', return_value=summary), patch(
        'services.wish_list_budget.fetch_category_display_names',
        return_value={},
    ), patch(
        'services.wish_list_budget.find_applicable_budget_candidate',
        return_value=candidate,
    ):
        impact = build_wish_list_budget_impact(
            tenant,
            5000,
            assigned_level=1,
            category_node_id='c1',
            category_l1_id='c1',
        )

    assert impact.has_budget is True
    assert impact.is_ahead_if_purchased is True
    assert impact.remaining_if_purchased == 0.0


def test_budget_impact_fail_open_without_summary():
    tenant = TenantContext.personal('user-1')
    with patch('services.wish_list_budget.fetch_budget_summary', return_value=None):
        impact = build_wish_list_budget_impact(
            tenant,
            1000,
            assigned_level=1,
            category_node_id='c1',
            category_l1_id='c1',
        )
    assert impact.has_budget is False
    assert impact.is_ahead_if_purchased is False


def test_budget_impact_cascades_to_l1_when_l2_undefined():
    tenant = TenantContext.personal('user-1')
    summary = {
        'has_any_limit': True,
        'budget_month': '2026-07-01',
        'fiscal_start_day': 1,
        'elapsed_days': 10,
        'days_in_month': 30,
        'budgets': [
            {'budget_level': 'l1', 'category_node_id': 'l1-id', 'amount': 50000},
            {'budget_level': 'total', 'category_node_id': None, 'amount': 100000},
        ],
        'spent_by_bucket': {'l1:l1-id': 20000, 'total': 25000},
    }
    with patch('services.wish_list_budget.fetch_budget_summary', return_value=summary), patch(
        'services.wish_list_budget.fetch_category_display_names',
        return_value={'l2-id': '电子游戏', 'l1-id': '休闲'},
    ):
        impact = build_wish_list_budget_impact(
            tenant,
            22500,
            assigned_level=2,
            category_node_id='l2-id',
            category_l1_id='l1-id',
            language='zh',
        )

    assert impact.has_budget is True
    assert impact.level == 'l1'
    assert impact.label == '休闲'
    assert impact.remaining_now == 30000.0
    assert impact.remaining_if_purchased == 7500.0


def test_budget_impact_uses_fiscal_month_not_calendar_month_start():
    """Regression: fiscal_start_day=24 stores budgets on 2026-07-24, not 2026-07-01."""
    tenant = TenantContext.group('group-1', 'user-1')
    fiscal_summary = {
        'has_any_limit': True,
        'budget_month': '2026-07-24',
        'fiscal_start_day': 24,
        'elapsed_days': 4,
        'days_in_month': 31,
        'budgets': [
            {'budget_level': 'l1', 'category_node_id': 'l1-leisure', 'amount': 60000},
            {'budget_level': 'total', 'category_node_id': None, 'amount': 600000},
        ],
        'spent_by_bucket': {'l1:l1-leisure': 10000, 'total': 50000},
    }
    fetch_calls: list[date] = []

    def fake_fetch(_tenant, budget_month, currency='JPY'):
        fetch_calls.append(budget_month)
        if budget_month == date(2026, 7, 24):
            return fiscal_summary
        return {'has_any_limit': False, 'budgets': [], 'spent_by_bucket': {}}

    with patch('services.wish_list_budget.fetch_budget_summary', side_effect=fake_fetch), patch(
        'services.wish_list_budget.resolve_budget_month_for_tenant',
        return_value=date(2026, 7, 24),
    ), patch(
        'services.wish_list_budget.fetch_category_display_names',
        return_value={'l2-games': '电子游戏', 'l1-leisure': '休闲'},
    ):
        impact = build_wish_list_budget_impact(
            tenant,
            22500,
            assigned_level=2,
            category_node_id='l2-games',
            category_l1_id='l1-leisure',
            as_of_date=date(2026, 7, 27),
            language='zh',
        )

    assert fetch_calls == [date(2026, 7, 24)]
    assert impact.has_budget is True
    assert impact.level == 'l1'
    assert impact.label == '休闲'
