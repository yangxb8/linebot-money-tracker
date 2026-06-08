import unittest

from services.tenant_context import (
    TenantContext,
    resolve_tenant_for_console,
    resolve_tenant_from_event,
)


class TestTenantContext(unittest.TestCase):
    def test_personal_tenant(self):
        tenant = TenantContext.personal('user-a')
        self.assertEqual(tenant.tenant_type, 'user')
        self.assertEqual(tenant.tenant_id, 'user-a')
        self.assertFalse(tenant.is_shared)

    def test_group_tenant(self):
        tenant = TenantContext.group('group-1', 'user-a')
        self.assertEqual(tenant.tenant_type, 'group')
        self.assertEqual(tenant.tenant_id, 'group-1')
        self.assertTrue(tenant.is_shared)

    def test_resolve_group_from_event(self):
        class DummySource:
            type = 'group'
            group_id = 'g-123'

        class DummyEvent:
            source = DummySource()

        tenant = resolve_tenant_from_event(DummyEvent(), 'user-a')
        self.assertEqual(tenant.tenant_type, 'group')
        self.assertEqual(tenant.tenant_id, 'g-123')
        self.assertEqual(tenant.logged_by_line_user_id, 'user-a')

    def test_resolve_room_from_event(self):
        class DummySource:
            type = 'room'
            room_id = 'r-456'

        class DummyEvent:
            source = DummySource()

        tenant = resolve_tenant_from_event(DummyEvent(), 'user-b')
        self.assertEqual(tenant.tenant_type, 'room')
        self.assertEqual(tenant.tenant_id, 'r-456')

    def test_console_group_flag(self):
        tenant = resolve_tenant_for_console('user-a', group_id='g-1')
        self.assertEqual(tenant.tenant_type, 'group')
        self.assertEqual(tenant.tenant_id, 'g-1')


if __name__ == '__main__':
    unittest.main()
