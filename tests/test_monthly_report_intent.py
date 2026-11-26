"""Intent classification tests for monthly_report."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from services.intent import _parse_combined_intent_response, classify_text_message_intent
from services.monthly_report import looks_like_monthly_report_intent


class TestMonthlyReportPhraseGate(unittest.TestCase):
    def test_english_phrases(self):
        self.assertTrue(looks_like_monthly_report_intent('monthly report'))
        self.assertTrue(looks_like_monthly_report_intent('Show my budget report'))
        self.assertTrue(looks_like_monthly_report_intent('expense report please'))

    def test_japanese_phrases(self):
        self.assertTrue(looks_like_monthly_report_intent('レポート見せて'))
        self.assertTrue(looks_like_monthly_report_intent('先月のまとめ'))
        self.assertTrue(looks_like_monthly_report_intent('家計レポート'))

    def test_non_report_text(self):
        self.assertFalse(looks_like_monthly_report_intent('Lunch 1200 yen'))
        self.assertFalse(looks_like_monthly_report_intent('I want to buy headphones'))
        self.assertFalse(looks_like_monthly_report_intent(''))


class TestMonthlyReportLlmParse(unittest.TestCase):
    def test_parses_monthly_report_intent_json(self):
        self.assertEqual(
            _parse_combined_intent_response('{"intent": "monthly_report"}'),
            'monthly_report',
        )


class TestMonthlyReportClassifyAsync(unittest.IsolatedAsyncioTestCase):
    async def test_phrase_gate_short_circuits_llm(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(return_value='{"intent": "other"}')
        result = await classify_text_message_intent('monthly report', gemini)
        self.assertEqual(result, 'monthly_report')
        gemini.generate_reply.assert_not_awaited()

    async def test_llm_monthly_report_when_no_phrase(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(return_value='{"intent": "monthly_report"}')
        # Avoid phrase gate with a vague ask
        result = await classify_text_message_intent(
            'Can you summarize how I did against budget last cycle?',
            gemini,
        )
        self.assertEqual(result, 'monthly_report')
