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

    return (
        'You write a single short budget pace warning for a LINE chat reply.\n'
        f'{voice}\n'
        f'Language: {language}\n'
        f'Budget level: {level_label} ({display_name})\n'
        f'Remaining budget: ¥{int(max(remaining, 0)):,}\n'
        f'Days left in month: {days_remaining}\n'
        f'Recommended daily spend: ¥{daily_allowance:,}\n'
        'The user is spending faster than expected this month.\n'
        'Write 1-2 sentences in the requested voice. Start with an emoji unless told to avoid emoji. '
        'Include the daily ¥ figure. Do not repeat expense details.'
    )
