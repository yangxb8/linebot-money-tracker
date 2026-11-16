"""Unit tests for process_audio_message transcription handoff."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.audio_limits import MAX_AUDIO_DURATION_MS, max_audio_bytes
from services.message_context import BotReply, MessageContext
from services.message_handler import process_audio_message
from services.tenant_context import TenantContext


@pytest.mark.asyncio
async def test_process_audio_delegates_transcript_to_text_path():
    gemini = MagicMock()
    context = MessageContext(
        tenant=TenantContext.personal('U-test'),
        source_message_id='msg-audio-1',
        reply_language='en',
    )
    expected = BotReply(text='Detected expense(s):\nLunch')

    with patch(
        'services.message_handler.transcribe_audio',
        AsyncMock(return_value='Lunch 1200 yen'),
    ) as transcribe_mock, patch(
        'services.message_handler.process_text_message',
        AsyncMock(return_value=expected),
    ) as text_mock:
        result = await process_audio_message(
            b'fake-audio',
            gemini,
            context=context,
            duration_ms=5_000,
        )

    assert result is expected
    transcribe_mock.assert_awaited_once()
    text_mock.assert_awaited_once()
    assert text_mock.await_args.args[0] == 'Lunch 1200 yen'


@pytest.mark.asyncio
async def test_process_audio_rejects_over_duration_without_transcription():
    gemini = MagicMock()
    with patch(
        'services.message_handler.transcribe_audio',
        AsyncMock(),
    ) as transcribe_mock:
        result = await process_audio_message(
            b'fake-audio',
            gemini,
            duration_ms=MAX_AUDIO_DURATION_MS + 1,
        )

    transcribe_mock.assert_not_awaited()
    assert '60' in result.text


@pytest.mark.asyncio
async def test_process_audio_rejects_over_size_without_transcription():
    gemini = MagicMock()
    oversized = b'x' * (max_audio_bytes() + 1)
    with patch(
        'services.message_handler.transcribe_audio',
        AsyncMock(),
    ) as transcribe_mock:
        result = await process_audio_message(oversized, gemini, duration_ms=1_000)

    transcribe_mock.assert_not_awaited()
    assert '5' in result.text


@pytest.mark.asyncio
async def test_process_audio_empty_transcript_unusable():
    gemini = MagicMock()
    with patch(
        'services.message_handler.transcribe_audio',
        AsyncMock(return_value='   '),
    ), patch(
        'services.message_handler.process_text_message',
        AsyncMock(),
    ) as text_mock:
        result = await process_audio_message(b'fake-audio', gemini, duration_ms=1_000)

    text_mock.assert_not_awaited()
    assert result.text  # localized unusable guidance
