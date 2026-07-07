"""Integration checks for 014 quickstart (T030) and SC-001 logic (T031)."""

import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from services.ai_assist import ReceiptImageParseResult
from services.gemini_client import GeminiClient
from services.message_context import MessageContext
from services.merchant_resolve import merchant_key_from_expense_row, resolve_raw_merchant
from services.receipt_store_name import propagate_receipt_store_name
from services.tenant_context import TenantContext
from tests.persona_test_utils import PERSONA_EXPENSE_HEADER_EN


def sc001_line_share_rate(items: list[dict]) -> float:
    """Fraction of lines whose merchant_key matches store header (not product heuristic)."""
    if not items:
        return 0.0
    store_name = items[0].get('store_name')
    if not store_name:
        return 0.0

    store_row = {'description': '', 'metadata': {'store_name': store_name}}
    store_key = merchant_key_from_expense_row(store_row)
    if not store_key:
        return 0.0

    matched = 0
    for item in items:
        line_key = merchant_key_from_expense_row(
            {
                'description': str(item.get('description', '')),
                'metadata': {'store_name': store_name},
            }
        )
        product_key = merchant_key_from_expense_row(
            {'description': str(item.get('description', '')), 'metadata': {}}
        )
        if line_key == store_key and line_key != product_key:
            matched += 1
    return matched / len(items)


class Test014QuickstartIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_image_pipeline_end_to_end_with_mocked_vision(self):
        """T030: mocked vision → propagate → items ready for categorize/persist."""
        from services.message_handler import _extract_expense_items_from_image

        gemini = MagicMock(spec=GeminiClient)
        llm_result = ReceiptImageParseResult(
            items=[
                {'description': '牛乳', 'amount': 198, 'currency': 'JPY'},
                {'description': '食パン', 'amount': 128, 'currency': 'JPY'},
                {'description': '鶏卵', 'amount': 98, 'currency': 'JPY'},
            ],
            total=Decimal('424'),
            currency='JPY',
            store_name='イオン',
        )

        with patch(
            'services.message_handler.preprocess_receipt_image',
            return_value=(b'jpeg', 'image/jpeg'),
        ), patch(
            'services.message_handler.assist_parse_image',
            AsyncMock(return_value=llm_result),
        ):
            items = await _extract_expense_items_from_image(b'fake', gemini, 'image/jpeg')

        self.assertEqual(len(items), 3)
        for item in items:
            self.assertEqual(item.get('store_name'), 'イオン')

    async def test_store_name_skips_merchant_llm_in_classify_path(self):
        gemini = MagicMock(spec=GeminiClient)
        with patch(
            'services.merchant_extract.extract_merchant_name',
            AsyncMock(),
        ) as extract_mock:
            raw, key = await resolve_raw_merchant(
                {'description': '牛乳', 'store_name': 'イオン', 'amount': 198, 'currency': 'JPY'},
                gemini,
            )
        extract_mock.assert_not_awaited()
        self.assertEqual(key, 'aeon')
        self.assertEqual(raw, 'イオン')

    def test_sc001_fixture_meets_seventy_percent_threshold(self):
        """T031: multi-line Aeon fixture should share store merchant_key on all lines."""
        items = propagate_receipt_store_name(
            [
                {'description': '牛乳', 'amount': 198, 'currency': 'JPY'},
                {'description': '食パン', 'amount': 128, 'currency': 'JPY'},
                {'description': '鶏卵', 'amount': 98, 'currency': 'JPY'},
                {'description': 'バナナ', 'amount': 158, 'currency': 'JPY'},
            ],
            'イオン',
        )
        rate = sc001_line_share_rate(items)
        self.assertGreaterEqual(rate, 0.70)
        self.assertEqual(rate, 1.0)

    async def test_process_image_message_full_handler_with_persist_mock(self):
        """T030: process_image_message returns confirmation when persist succeeds."""
        from services.categorize import CategoryResultWithProvenance
        from services.expense_repository import PersistResult
        from services.message_handler import process_image_message

        gemini = MagicMock(spec=GeminiClient)
        context = MessageContext(
            tenant=TenantContext.personal('u1'),
            source_message_id='msg-sc001',
            reply_language='en',
        )
        llm_result = ReceiptImageParseResult(
            items=[
                {'description': '牛乳', 'amount': 198, 'currency': 'JPY'},
                {'description': '食パン', 'amount': 128, 'currency': 'JPY'},
            ],
            total=Decimal('326'),
            currency='JPY',
            store_name='イオン',
        )

        with patch(
            'services.message_handler.preprocess_receipt_image',
            return_value=(b'jpeg', 'image/jpeg'),
        ), patch(
            'services.message_handler.assist_parse_image',
            AsyncMock(return_value=llm_result),
        ), patch(
            'services.message_handler.classify_expense_with_memory',
            AsyncMock(
                return_value=CategoryResultWithProvenance(
                    guessed='food.grocery',
                    alternatives=(),
                    source='llm',
                    merchant_key='aeon',
                )
            ),
        ), patch(
            'services.message_handler.insert_expenses',
            return_value=PersistResult(inserted=2, skipped=0),
        ), patch(
            'services.message_handler.fetch_expense_ids_for_message',
            return_value=[
                {'id': 'e0', 'line_item_index': 0},
                {'id': 'e1', 'line_item_index': 1},
            ],
        ):
            reply = await process_image_message(b'fake', gemini, context=context)

        self.assertIn(PERSONA_EXPENSE_HEADER_EN, reply.text)


if __name__ == '__main__':
    unittest.main()
