"""Guardrails for voice transcription prompt amount normalization."""

from services.ai_assist import _AUDIO_TRANSCRIBE_PROMPT


def test_audio_transcribe_prompt_requires_arabic_digit_amounts():
    prompt = _AUDIO_TRANSCRIBE_PROMPT
    assert 'Arabic digits' in prompt or 'arabic digits' in prompt.lower()
    assert '1200円' in prompt
    assert '万' in prompt
    assert 'digit-by-digit' in prompt.lower() or 'イチニーゼロゼロ' in prompt
    assert '{"transcript"' in prompt.replace(' ', '')
