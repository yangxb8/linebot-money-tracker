"""LLM prompt builder for budget pace warnings."""

from __future__ import annotations

from typing import Literal

from services.bot_persona import PersonaConfig, persona_voice_instructions

BudgetLevel = Literal['l2', 'l1', 'total']


def build_budget_pace_prompt(
    *,
    language: str,
    level: BudgetLevel,
    display_name: str,
    remaining: float,
    limit: float,
    spent: float,
    over_amount: int,
    spent_pct: int,
    is_over_budget: bool,
    days_remaining: int,
    daily_allowance: int,
    persona: PersonaConfig,
) -> str:
    level_label = {
        'l2': 'L2 category',
        'l1': 'L1 category group',
        'total': 'total monthly budget',
    }[level]

    voice = persona_voice_instructions(persona, language)

    if is_over_budget:
        status_block = (
            f'Budget limit: ¥{int(limit):,}\n'
            f'Amount spent: ¥{int(spent):,}\n'
            f'Over budget by: ¥{over_amount:,}\n'
            f'Percent of limit spent: {spent_pct}%\n'
            'The user has exceeded their budget for this category/level.\n'
            'Write 1-2 sentences in the requested voice. Start with an emoji unless told to avoid emoji. '
            'State how much they are over budget and what percent of the limit they have spent. '
            'Do NOT suggest a daily spending amount. Do not repeat expense details.'
        )
    else:
        status_block = (
            f'Remaining budget: ¥{int(max(remaining, 0)):,}\n'
            f'Days left in month: {days_remaining}\n'
            f'Recommended daily spend: ¥{daily_allowance:,}\n'
            'The user is spending faster than expected this month.\n'
            'Write 1-2 sentences in the requested voice. Start with an emoji unless told to avoid emoji. '
            'Include the daily ¥ figure. Do not repeat expense details.'
        )

    return (
        'You write a single short budget pace warning for a LINE chat reply.\n'
        f'{voice}\n'
        f'Language: {language}\n'
        f'Budget level: {level_label} ({display_name})\n'
        f'{status_block}'
    )
