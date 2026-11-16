"""Voice/audio abuse limits for LINE inbound messages (feature 022)."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from services.usage_config import get_free_tier_limits

# Product default: 60 seconds (inclusive).
MAX_AUDIO_DURATION_MS = 60_000


class AudioLimitViolation(str, Enum):
    DURATION = 'duration'
    SIZE = 'size'


def max_audio_bytes() -> int:
    return get_free_tier_limits().max_audio_bytes


def check_audio_duration(duration_ms: Optional[int]) -> Optional[AudioLimitViolation]:
    """Return DURATION when duration_ms is known and strictly greater than max."""
    if duration_ms is None:
        return None
    try:
        value = int(duration_ms)
    except (TypeError, ValueError):
        return None
    if value > MAX_AUDIO_DURATION_MS:
        return AudioLimitViolation.DURATION
    return None


def check_audio_size(audio_bytes: bytes) -> Optional[AudioLimitViolation]:
    """Return SIZE when byte length is strictly greater than max."""
    if len(audio_bytes) > max_audio_bytes():
        return AudioLimitViolation.SIZE
    return None
