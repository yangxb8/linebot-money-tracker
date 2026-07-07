from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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


def _persona_suffix(language: str, *, emoji_level: int) -> str:
    # Keep these short and deterministic to avoid changing meaning.
    if emoji_level == EMOJI_LEVEL_OFF:
        emoji = ''
    elif emoji_level == EMOJI_LEVEL_LIGHT:
        emoji = ' 🐰'
    else:
        emoji = ' 🐰✨'

    lang = (language or 'ja').lower()
    if lang.startswith('en'):
        return f'Got it.{emoji}'
    if lang.startswith('zh'):
        return f'收到。{emoji}'.strip()
    # default ja
    return f'了解だよ。{emoji}'.strip()


def apply_persona_style(
    raw_reply_text: str,
    *,
    language: str,
    persona: PersonaConfig,
) -> str:
    """Apply a lightweight persona wrapper without changing factual content.

    Rules:
    - Only add a short prefix and spacing.
    - Never rewrite the body (avoids corrupting amounts/IDs).
    """
    body = (raw_reply_text or '').strip()
    if not body:
        return body

    # v1: only one preset, but keep gate for future presets.
    if persona.preset not in PERSONA_PRESETS:
        persona = PersonaConfig()

    suffix = _persona_suffix(language, emoji_level=persona.emoji_level)
    if not suffix.strip():
        return body

    return f'{body}\n\n{suffix}'
