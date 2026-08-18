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
        'pace_tight_l2': (
            '⚠️ **{name}** の支出ペースが速いです。'
            '残り予算はわずか¥{remaining:,}（{days}日間）。'
        ),
        'pace_tight_l1': (
            '⚠️ **{name}**（大カテゴリ）の支出ペースが速いです。'
            '残り予算はわずか¥{remaining:,}（{days}日間）。'
        ),
        'pace_tight_total': (
            '⚠️ 今月の**総予算**のペースが速いです。'
            '残り予算はわずか¥{remaining:,}（{days}日間）。'
        ),
        'pace_over_l2': (
            '⚠️ **{name}** の予算を¥{over:,}超過しています'
            '（予算の{pct}%を使用）。'
        ),
        'pace_over_l1': (
            '⚠️ **{name}**（大カテゴリ）の予算を¥{over:,}超過しています'
            '（予算の{pct}%を使用）。'
        ),
        'pace_over_total': (
            '⚠️ 今月の**総予算**を¥{over:,}超過しています'
            '（予算の{pct}%を使用）。'
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
        'pace_tight_l2': (
            "⚠️ You're spending **{name}** too fast. "
            'Only ¥{remaining:,} left for the next {days} days.'
        ),
        'pace_tight_l1': (
            "⚠️ You're ahead of pace on **{name}** (category group). "
            'Only ¥{remaining:,} left for the next {days} days.'
        ),
        'pace_tight_total': (
            "⚠️ You're ahead of your **total budget** pace. "
            'Only ¥{remaining:,} left for the next {days} days.'
        ),
        'pace_over_l2': (
            "⚠️ **{name}** is ¥{over:,} over budget "
            '({pct}% of limit spent).'
        ),
        'pace_over_l1': (
            "⚠️ **{name}** (category group) is ¥{over:,} over budget "
            '({pct}% of limit spent).'
        ),
        'pace_over_total': (
            "⚠️ You're ¥{over:,} over your **total budget** "
            '({pct}% of limit spent).'
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
        'pace_tight_l2': (
            '⚠️ **{name}** 支出速度过快。'
            '仅剩 ¥{remaining:,}（{days} 天）。'
        ),
        'pace_tight_l1': (
            '⚠️ **{name}**（大类）支出速度过快。'
            '仅剩 ¥{remaining:,}（{days} 天）。'
        ),
        'pace_tight_total': (
            '⚠️ 本月**总预算**支出速度过快。'
            '仅剩 ¥{remaining:,}（{days} 天）。'
        ),
        'pace_over_l2': (
            '⚠️ **{name}** 已超预算 ¥{over:,}（已用 {pct}%）。'
        ),
        'pace_over_l1': (
            '⚠️ **{name}**（大类）已超预算 ¥{over:,}（已用 {pct}%）。'
        ),
        'pace_over_total': (
            '⚠️ 本月**总预算**已超 ¥{over:,}（已用 {pct}%）。'
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
    limit: float,
    spent: float,
    language: str,
) -> str:
    lang = _lang(language)
    strings = _STRINGS[lang]

    if spent > limit:
        over = int(spent - limit)
        pct = int(round(spent / limit * 100)) if limit > 0 else 0
        key = f'pace_over_{level}'
        return strings[key].format(name=display_name, over=over, pct=pct)

    if remaining <= 0:
        key = f'pace_exhausted_{level}'
        return strings[key].format(name=display_name)

    if daily_allowance <= 0 and remaining > 0:
        key = f'pace_tight_{level}'
        return strings[key].format(
            name=display_name,
            remaining=int(remaining),
            days=days_remaining,
        )

    key = f'pace_warning_{level}'
    return strings[key].format(
        name=display_name,
        daily=daily_allowance,
        days=days_remaining,
    )


def total_budget_label(language: str) -> str:
    return _STRINGS[_lang(language)]['total_label']
