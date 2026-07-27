from decimal import Decimal

from services.bot_persona import DEFAULT_PERSONA_PRESET, PersonaConfig, persona_scope
from services.wish_list import (
    WishListCandidate,
    format_wish_budget_impact_lines,
    format_wish_list_ask_details,
)
from services.wish_list_budget import WishBudgetImpact


def test_ask_details_uses_judy_persona_when_active():
    with persona_scope(PersonaConfig(preset=DEFAULT_PERSONA_PRESET)):
        text = format_wish_list_ask_details('zh')
    assert '🐰' in text
    assert '30秒' in text
    assert '回复这条消息' not in text


def test_pace_warning_line_when_ahead():
    impact = WishBudgetImpact(
        has_budget=True,
        level='l1',
        label='休闲',
        limit=50000.0,
        spent_now=20000.0,
        remaining_now=30000.0,
        remaining_if_purchased=7500.0,
        is_ahead_if_purchased=True,
        days_remaining=20,
        daily_allowance_if_purchased=375.0,
    )
    lines = format_wish_budget_impact_lines(impact, 'zh')
    assert len(lines) == 2
    assert '预算' in lines[0]
    assert '偏快' in lines[1] or '⚠️' in lines[1]


def test_no_pace_warning_when_on_pace():
    impact = WishBudgetImpact(
        has_budget=True,
        level='total',
        label='Total',
        limit=100000.0,
        spent_now=20000.0,
        remaining_now=80000.0,
        remaining_if_purchased=75000.0,
        is_ahead_if_purchased=False,
        days_remaining=20,
        daily_allowance_if_purchased=3750.0,
    )
    lines = format_wish_budget_impact_lines(impact, 'en')
    assert len(lines) == 1
    assert 'Budget' in lines[0]
