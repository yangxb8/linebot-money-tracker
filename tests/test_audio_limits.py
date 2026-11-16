"""Unit tests for voice/audio abuse limits (feature 022)."""

from services.audio_limits import (
    MAX_AUDIO_DURATION_MS,
    AudioLimitViolation,
    check_audio_duration,
    check_audio_size,
    max_audio_bytes,
)


def test_duration_at_max_accepted():
    assert check_audio_duration(MAX_AUDIO_DURATION_MS) is None


def test_duration_over_max_rejected():
    assert check_audio_duration(MAX_AUDIO_DURATION_MS + 1) == AudioLimitViolation.DURATION


def test_duration_none_skips_check():
    assert check_audio_duration(None) is None


def test_size_at_max_accepted():
    limit = max_audio_bytes()
    assert check_audio_size(b'x' * limit) is None


def test_size_over_max_rejected():
    limit = max_audio_bytes()
    assert check_audio_size(b'x' * (limit + 1)) == AudioLimitViolation.SIZE
