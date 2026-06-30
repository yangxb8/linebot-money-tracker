"""Template fallback strings for budget pace warnings."""

from __future__ import annotations

from typing import Literal

BudgetLevel = Literal['l2', 'l1', 'total']

_STRINGS: dict[str, dict[str, str]] = {
    'ja': {
        'pace_warning_l2': (
            '⚠️ **{name}** の支出ペースが速いです。'
            '残り{days}日は1日約¥{daily:,}までが目安です。'
        ),
        'pace_warning_l1': (
            '⚠️ **{name}**（大カテゴリ）の支出ペースが速いです。'
            '残り{days}日は1日約¥{daily:,}までが目安です。'
        ),
        'pace_warning_total': (
            '⚠️ 今月の**総予算**のペースが速いです。'
            '残り{days}日は1日約¥{daily:,}までが目安です。'
        ),
        'pace_exhausted_l2': '⚠️ **{name}** の予算を使い切りました。',
        'pace_exhausted_l1': '⚠️ **{name}**（大カテゴリ）の予算を使い切りました。',
        'pace_exhausted_total': '⚠️ 今月の**総予算**を使い切りました。',
        'total_label': '総予算',
    },
    'en': {
        'pace_warning_l2': (
            "⚠️ You're spending **{name}** too fast. "
            'Aim for about ¥{daily:,}/day for the next {days} days.'
        ),
        'pace_warning_l1': (
            "⚠️ You're ahead of pace on **{name}** (category group). "
            'Aim for about ¥{daily:,}/day for the next {days} days.'
        ),
        'pace_warning_total': (
            "⚠️ You're ahead of your **total budget** pace. "
            'Aim for about ¥{daily:,}/day for the next {days} days.'
        ),
        'pace_exhausted_l2': "⚠️ You've used up the **{name}** budget.",
        'pace_exhausted_l1': "⚠️ You've used up the **{name}** category group budget.",
        'pace_exhausted_total': "⚠️ You've used up your **total budget** for this month.",
        'total_label': 'Total budget',
    },
    'zh': {
        'pace_warning_l2': (
            '⚠️ **{name}** 支出速度过快。'
            '剩余{days}天，建议每天约¥{daily:,}以内。'
        ),
        'pace_warning_l1': (
            '⚠️ **{name}**（大类）支出速度过快。'
            '剩余{days}天，建议每天约¥{daily:,}以内。'
        ),
        'pace_warning_total': (
            '⚠️ 本月**总预算**支出速度过快。'
            '剩余{days}天，建议每天约¥{daily:,}以内。'
        ),
        'pace_exhausted_l2': '⚠️ **{name}** 预算已用尽。',
        'pace_exhausted_l1': '⚠️ **{name}**（大类）预算已用尽。',
        'pace_exhausted_total': '⚠️ 本月**总预算**已用尽。',
        'total_label': '总预算',
    },
}


def _lang(language: str) -> str:
    if language in _STRINGS:
        return language
    if language.startswith('zh'):
        return 'zh'
    if language.startswith('en'):
        return 'en'
    return 'ja'


def format_pace_warning_template(
    *,
    level: BudgetLevel,
    display_name: str,
    daily_allowance: int,
    days_remaining: int,
    remaining: float,
    language: str,
) -> str:
    lang = _lang(language)
    strings = _STRINGS[lang]
    if remaining <= 0:
        key = f'pace_exhausted_{level}'
        return strings[key].format(name=display_name)

    key = f'pace_warning_{level}'
    return strings[key].format(
        name=display_name,
        daily=daily_allowance,
        days=days_remaining,
    )


def total_budget_label(language: str) -> str:
    return _STRINGS[_lang(language)]['total_label']
