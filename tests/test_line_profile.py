import unittest
from unittest.mock import AsyncMock, MagicMock

from services.line_profile import fetch_line_display_name
from services.tenant_context import TenantContext


class TestLineProfile(unittest.IsolatedAsyncioTestCase):
    async def test_group_member_display_name(self):
        api = MagicMock()
        api.get_group_member_profile = AsyncMock(return_value=MagicMock(display_name='Bob'))
        tenant = TenantContext.group('g1', 'u1')

        name = await fetch_line_display_name(api, tenant, 'u1')

        self.assertEqual(name, 'Bob')
        api.get_group_member_profile.assert_awaited_once_with('g1', 'u1')

    async def test_room_member_display_name(self):
        api = MagicMock()
        api.get_room_member_profile = AsyncMock(return_value=MagicMock(display_name='Carol'))
        tenant = TenantContext.room('r1', 'u1')

        name = await fetch_line_display_name(api, tenant, 'u1')

        self.assertEqual(name, 'Carol')
        api.get_room_member_profile.assert_awaited_once_with('r1', 'u1')

    async def test_personal_profile_display_name(self):
        api = MagicMock()
        api.get_profile = AsyncMock(return_value=MagicMock(display_name='Dave'))
        tenant = TenantContext.personal('u1')

        name = await fetch_line_display_name(api, tenant, 'u1')

        self.assertEqual(name, 'Dave')
        api.get_profile.assert_awaited_once_with('u1')


if __name__ == '__main__':
    unittest.main()
