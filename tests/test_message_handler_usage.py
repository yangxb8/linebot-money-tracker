import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.message_context import MessageContext
from services.tenant_context import TenantContext
from services.message_handler import process_text_message


class TestMessageHandlerUsage(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_parse_skips_intent(self):
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock()
        context = MessageContext(tenant=TenantContext.personal('u1'), source_message_id='m1')
        with (
            patch(
                'services.message_handler.parse_text_for_expenses',
                return_value=[{'description': 'Lunch', 'amount': 120, 'currency': 'JPY'}],
            ),
            patch(
                'services.message_handler._enrich_and_persist_items',
                new_callable=AsyncMock,
                return_value=([], None),
            ),
            patch(
                'services.message_handler.classify_text_message_intent',
                new_callable=AsyncMock,
            ) as intent_mock,
        ):
            await process_text_message('Lunch 1200 yen', gemini, context)
        intent_mock.assert_not_awaited()
        gemini.generate_reply.assert_not_called()


if __name__ == '__main__':
    unittest.main()
