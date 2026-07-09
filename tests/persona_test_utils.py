"""Helpers for persona-related tests."""

from services.bot_persona import PersonaConfig, persona_scope

# Preset not in persona tables — forces neutral confirmation_i18n strings.
NEUTRAL_PERSONA = PersonaConfig(preset='neutral')

PERSONA_EXPENSE_HEADER_EN = '🐰✨ Expenses I spotted:'


def with_neutral_persona():
    return persona_scope(NEUTRAL_PERSONA)
