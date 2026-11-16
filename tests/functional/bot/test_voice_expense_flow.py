"""Scenarios: bot.voice.expense_confirm / reject_over_duration / reject_over_size / unusable."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.audio_limits import MAX_AUDIO_DURATION_MS, max_audio_bytes
from services.categorize import CategoryResultWithProvenance
from services.expense_repository import PersistResult
from tests.functional.bot.conftest import assert_callback_ok, post_signed
from tests.functional.bot.helpers.webhook_events import audio_message_event, webhook_body


def _unknown_category():
    return CategoryResultWithProvenance(guessed="unknown", alternatives=(), source="llm")


@pytest.mark.functional
def test_bot_voice_expense_confirm(client, reply_mock):
    """Signed audio webhook → confirmation reply; expense insert; Gemini mocked."""
    body = webhook_body(
        audio_message_event(message_id="msg-voice-1", duration_ms=4_000),
    )
    insert_mock = MagicMock(return_value=PersistResult(inserted=1, skipped=0))
    transcribe_mock = AsyncMock(return_value="Lunch 1200 yen")
    fetch_mock = AsyncMock(return_value=b"fake-m4a-bytes")

    with patch("main.save_inbound_audio_message"), patch(
        "main._fetch_message_content_bytes",
        fetch_mock,
    ), patch(
        "services.message_handler.transcribe_audio",
        transcribe_mock,
    ), patch(
        "services.message_handler.classify_text_message_intent",
        AsyncMock(return_value="expense"),
    ), patch(
        "services.message_handler.parse_text_for_expenses",
        return_value=[{"description": "Lunch", "amount": 1200.0, "currency": "JPY"}],
    ), patch(
        "services.message_handler.classify_expense_with_memory",
        AsyncMock(return_value=_unknown_category()),
    ), patch(
        "services.message_handler.insert_expenses",
        insert_mock,
    ):
        response = post_signed(client, body)

    assert_callback_ok(response)
    fetch_mock.assert_awaited()
    transcribe_mock.assert_awaited()
    insert_mock.assert_called()
    reply_mock.assert_awaited()
    message_text = reply_mock.call_args[0][0].messages[0].text
    assert "Lunch" in message_text or "✅" in message_text


@pytest.mark.functional
def test_bot_voice_reject_over_duration(client, reply_mock):
    """Duration over 60s → rejection; no content fetch / no transcription."""
    body = webhook_body(
        audio_message_event(
            message_id="msg-voice-long",
            duration_ms=MAX_AUDIO_DURATION_MS + 1,
        ),
    )
    fetch_mock = AsyncMock(return_value=b"should-not-fetch")
    transcribe_mock = AsyncMock(return_value="Lunch 1200 yen")
    insert_mock = MagicMock()

    with patch("main.save_inbound_audio_message"), patch(
        "main._fetch_message_content_bytes",
        fetch_mock,
    ), patch(
        "services.message_handler.transcribe_audio",
        transcribe_mock,
    ), patch(
        "services.message_handler.insert_expenses",
        insert_mock,
    ):
        response = post_signed(client, body)

    assert_callback_ok(response)
    fetch_mock.assert_not_awaited()
    transcribe_mock.assert_not_awaited()
    insert_mock.assert_not_called()
    reply_mock.assert_awaited()
    message_text = reply_mock.call_args[0][0].messages[0].text
    assert "60" in message_text


@pytest.mark.functional
def test_bot_voice_reject_over_size(client, reply_mock):
    """Audio bytes over 5 MiB → rejection; no transcription / no expense."""
    body = webhook_body(
        audio_message_event(message_id="msg-voice-big", duration_ms=3_000),
    )
    oversized = b"x" * (max_audio_bytes() + 1)
    fetch_mock = AsyncMock(return_value=oversized)
    transcribe_mock = AsyncMock(return_value="Lunch 1200 yen")
    insert_mock = MagicMock()

    with patch("main.save_inbound_audio_message"), patch(
        "main._fetch_message_content_bytes",
        fetch_mock,
    ), patch(
        "services.message_handler.transcribe_audio",
        transcribe_mock,
    ), patch(
        "services.message_handler.insert_expenses",
        insert_mock,
    ):
        response = post_signed(client, body)

    assert_callback_ok(response)
    fetch_mock.assert_awaited()
    transcribe_mock.assert_not_awaited()
    insert_mock.assert_not_called()
    reply_mock.assert_awaited()
    message_text = reply_mock.call_args[0][0].messages[0].text
    assert "5" in message_text


@pytest.mark.functional
def test_bot_voice_unusable_transcript(client, reply_mock):
    """Empty transcript → unusable guidance; no expense insert."""
    body = webhook_body(
        audio_message_event(message_id="msg-voice-empty", duration_ms=2_000),
    )
    insert_mock = MagicMock()

    with patch("main.save_inbound_audio_message"), patch(
        "main._fetch_message_content_bytes",
        AsyncMock(return_value=b"silent"),
    ), patch(
        "services.message_handler.transcribe_audio",
        AsyncMock(return_value=""),
    ), patch(
        "services.message_handler.insert_expenses",
        insert_mock,
    ):
        response = post_signed(client, body)

    assert_callback_ok(response)
    insert_mock.assert_not_called()
    reply_mock.assert_awaited()
    assert reply_mock.call_args[0][0].messages[0].text


@pytest.mark.functional
def test_bot_voice_wish_intent_parity(client, reply_mock):
    """Wish-intent transcript → wish propose path; no expense insert."""
    body = webhook_body(
        audio_message_event(message_id="msg-voice-wish", duration_ms=3_000),
    )
    insert_expense = MagicMock()

    with patch("main.save_inbound_audio_message"), patch(
        "main._fetch_message_content_bytes",
        AsyncMock(return_value=b"wish-audio"),
    ), patch(
        "services.message_handler.transcribe_audio",
        AsyncMock(return_value="I want to buy headphones 15000 yen"),
    ), patch(
        "services.message_handler.parse_text_for_expenses",
        return_value=[{"description": "headphones", "amount": 15000.0, "currency": "JPY"}],
    ), patch(
        "services.message_handler.classify_expense_with_memory",
        AsyncMock(return_value=_unknown_category()),
    ), patch(
        "services.message_handler.insert_expenses",
        insert_expense,
    ), patch(
        "services.wish_list_budget.build_wish_list_budget_impact",
        return_value=None,
    ):
        response = post_signed(client, body)

    assert_callback_ok(response)
    insert_expense.assert_not_called()
    reply_mock.assert_awaited()
    message_text = reply_mock.call_args[0][0].messages[0].text
    assert "headphones" in message_text.lower() or "wish" in message_text.lower() or "ウィッシュ" in message_text
