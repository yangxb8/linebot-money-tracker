"""Unit tests for monthly report PNG render + style helpers."""

from __future__ import annotations

from services.monthly_report_render import _chart_series, _theme_rgb, render_report_png
from services.monthly_report_repository import compute_style_fingerprint


def test_style_fingerprint_changes_with_persona_language_emoji():
    a = compute_style_fingerprint(
        language='en', persona_preset='judy_hopps', emoji_level=1, custom_text=''
    )
    b = compute_style_fingerprint(
        language='ja', persona_preset='judy_hopps', emoji_level=1, custom_text=''
    )
    c = compute_style_fingerprint(
        language='en', persona_preset='judy_hopps', emoji_level=2, custom_text=''
    )
    d = compute_style_fingerprint(
        language='en', persona_preset='default', emoji_level=1, custom_text=''
    )
    assert len({a, b, c, d}) == 4


def test_theme_overspend_severity_and_top_spend():
    food = _theme_rgb('Food / 外食', 'none')
    transport = _theme_rgb('Transport', 'none')
    high = _theme_rgb('Food', 'high')
    caution = _theme_rgb('Food', 'caution')
    assert food != transport
    assert high == (176, 58, 46)
    assert caution == (180, 110, 40)


def test_chart_series_budget_vs_actual_when_budgeted():
    series = _chart_series(
        {
            'has_any_budget': True,
            'total': {'limit': 100000, 'spent': 90000},
            'categories': [
                {'name': 'Food', 'limit': 30000, 'spent': 40000},
            ],
        }
    )
    assert series[0]['label'] == 'Total'
    assert series[0]['limit'] == 100000
    assert series[1]['label'] == 'Food'
    assert not any(s.get('fallback') for s in series)


def test_chart_series_fallback_spending_only():
    series = _chart_series(
        {
            'has_any_budget': False,
            'spending_total': 12345,
            'categories': [],
        }
    )
    assert len(series) == 1
    assert series[0].get('fallback') is True
    assert series[0]['spent'] == 12345


def test_render_png_produces_valid_png_bytes():
    png = render_report_png(
        snapshot={
            'has_any_budget': True,
            'total': {'limit': 100000, 'spent': 110000},
            'categories': [
                {'name': 'Food', 'limit': 30000, 'spent': 45000},
                {'name': 'Transport', 'limit': 10000, 'spent': 8000},
            ],
            'top_spend_category': {'id': 'food', 'name': 'Food'},
            'overspend_severity': 'high',
        },
        insight_text='Over budget this period.',
        period_label='Oct 2026',
        title='Monthly Report',
    )
    assert png.startswith(b'\x89PNG')
    assert len(png) > 500
