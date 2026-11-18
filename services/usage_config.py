"""Environment-driven free-tier usage limits."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return int(str(raw).strip())


@dataclass(frozen=True)
class UsageTierLimits:
    tier: str
    monthly_total: int
    monthly_receipt_analyses: int
    rate_per_minute: int
    rate_per_day: int
    max_text_words: int
    max_image_bytes: int


LIFETIME_BUCKET = 'lifetime'


def get_free_tier_limits() -> UsageTierLimits:
    return UsageTierLimits(
        tier='free',
        monthly_total=_int_env('USAGE_TIER_FREE_MONTHLY_TOTAL', 300),
        monthly_receipt_analyses=_int_env('USAGE_TIER_FREE_RECEIPT_MONTHLY', 100),
        rate_per_minute=_int_env('USAGE_RATE_LIMIT_PER_MINUTE', 10),
        rate_per_day=_int_env('USAGE_RATE_LIMIT_PER_DAY', 100),
        max_text_words=_int_env('USAGE_MAX_TEXT_WORDS', 1000),
        max_image_bytes=_int_env('USAGE_MAX_IMAGE_BYTES', 10 * 1024 * 1024),
    )
