import unittest
from unittest.mock import AsyncMock, MagicMock

from services.line_chat import fetch_chat_display_name
from services.tenant_context import TenantContext


class TestLineChat(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_chat_display_name_for_group(self):
        api = AsyncMock()
        api.get_group_summary = AsyncMock(return_value=MagicMock(group_name='Trip Fund'))
        tenant = TenantContext.group('g1', 'u1')

        name = await fetch_chat_display_name(api, tenant)

        self.assertEqual(name, 'Trip Fund')
        api.get_group_summary.assert_awaited_once_with('g1')

    async def test_fetch_chat_display_name_returns_none_for_personal(self):
        api = AsyncMock()
        tenant = TenantContext.personal('u1')

        name = await fetch_chat_display_name(api, tenant)

        self.assertIsNone(name)
        api.get_group_summary.assert_not_called()


if __name__ == '__main__':
    unittest.main()
