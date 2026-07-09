from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional

from services.tenant_context import TenantContext


DEFAULT_PERSONA_PRESET = 'judy_hopps_cute_firm'

# v1 allowlist (extensible)
PERSONA_PRESETS = {
    DEFAULT_PERSONA_PRESET,
}

EMOJI_LEVEL_OFF = 0
EMOJI_LEVEL_LIGHT = 1
EMOJI_LEVEL_NORMAL = 2
EMOJI_LEVEL_DEFAULT = EMOJI_LEVEL_NORMAL

EMOJI_LEVELS = {EMOJI_LEVEL_OFF, EMOJI_LEVEL_LIGHT, EMOJI_LEVEL_NORMAL}

# Keep short to reduce prompt-injection and UX risk.
MAX_CUSTOM_TEXT_LEN = 200

_active_persona: contextvars.ContextVar[Optional['PersonaConfig']] = contextvars.ContextVar(
    'active_persona',
    default=None,
)


@dataclass(frozen=True)
class PersonaConfig:
    preset: str = DEFAULT_PERSONA_PRESET
    custom_text: str = ''
    emoji_level: int = EMOJI_LEVEL_DEFAULT


def normalize_persona_config(
    *,
    preset: Optional[str],
    custom_text: Optional[str],
    emoji_level: Optional[int],
) -> PersonaConfig:
    normalized_preset = str(preset or '').strip()
    if normalized_preset not in PERSONA_PRESETS:
        normalized_preset = DEFAULT_PERSONA_PRESET

    text = (custom_text or '').strip()
    if len(text) > MAX_CUSTOM_TEXT_LEN:
        text = text[:MAX_CUSTOM_TEXT_LEN].rstrip()

    try:
        level = int(emoji_level) if emoji_level is not None else EMOJI_LEVEL_DEFAULT
    except (TypeError, ValueError):
        level = EMOJI_LEVEL_DEFAULT
    if level not in EMOJI_LEVELS:
        level = EMOJI_LEVEL_DEFAULT

    return PersonaConfig(preset=normalized_preset, custom_text=text, emoji_level=level)


def get_active_persona() -> PersonaConfig:
    persona = _active_persona.get()
    return persona if persona is not None else PersonaConfig()


@contextmanager
def persona_scope(persona: PersonaConfig) -> Iterator[None]:
    token = _active_persona.set(persona)
    try:
        yield
    finally:
        _active_persona.reset(token)


def resolve_persona_for_tenant(tenant: Optional[TenantContext]) -> PersonaConfig:
    if tenant is None:
        return PersonaConfig()
    from services.tenant_settings import fetch_tenant_bot_settings

    try:
        return fetch_tenant_bot_settings(tenant).persona
    except Exception:
        return PersonaConfig()


def persona_voice_instructions(persona: PersonaConfig, language: str) -> str:
    """Short style guidance for LLM-generated user-facing text."""
    lang = (language or 'ja').lower()
    custom = (persona.custom_text or '').strip()
    if persona.preset == DEFAULT_PERSONA_PRESET:
        if lang.startswith('en'):
            base = (
                'Voice: Judy Hopps-inspired — upbeat, cute but firm, encouraging. '
                'Use light emoji when natural.'
            )
        elif lang.startswith('zh'):
            base = '语气：朱迪·霍普斯风格——可爱但坚定、积极鼓励，自然点缀少量 emoji。'
        else:
            base = '口調：ジュディ風——かわいくもはっきり、励ましつつ。自然に軽い絵文字を使う。'
    else:
        base = 'Voice: friendly household expense assistant.'

    if persona.emoji_level == EMOJI_LEVEL_OFF:
        base += ' Avoid emoji.'
    elif persona.emoji_level == EMOJI_LEVEL_LIGHT:
        base += ' Use at most one emoji.'
    if custom:
        base += f' Tenant style note: {custom}'
    return base
