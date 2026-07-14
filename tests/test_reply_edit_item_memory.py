import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.reply_edit import _record_category_memory_correction
from services.gemini_client import GeminiClient
from services.tenant_context import TenantContext


class TestReplyEditItemMemory(unittest.IsolatedAsyncioTestCase):
    async def test_receipt_correction_uses_item_memory_not_merchant(self):
        gemini = MagicMock(spec=GeminiClient)
        confirmation = MagicMock()
        confirmation.tenant = TenantContext.personal('u1')

        with patch(
            'services.category_memory.record_item_user_correction_from_description',
            AsyncMock(),
        ) as item_mock, patch(
            'services.reply_edit.record_user_correction_from_description',
            AsyncMock(),
        ) as merchant_mock:
            await _record_category_memory_correction(
                confirmation,
                description='シャワートイレ用パルプ',
                category_code='living.daily',
                gemini=gemini,
                store_name='島忠ホームズ',
            )

        item_mock.assert_awaited_once()
        merchant_mock.assert_not_awaited()

    async def test_text_correction_uses_merchant_memory(self):
        gemini = MagicMock(spec=GeminiClient)
        confirmation = MagicMock()
        confirmation.tenant = TenantContext.personal('u1')

        with patch(
            'services.category_memory.record_item_user_correction_from_description',
            AsyncMock(),
        ) as item_mock, patch(
            'services.reply_edit.record_user_correction_from_description',
            AsyncMock(),
        ) as merchant_mock:
            await _record_category_memory_correction(
                confirmation,
                description='スターバックス ラテ',
                category_code='food.dining',
                gemini=gemini,
                store_name=None,
            )

        merchant_mock.assert_awaited_once()
        item_mock.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
