import os
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services.expense_repository import (
    ExpenseInsertRow,
    PersistResult,
    build_insert_row,
    insert_expenses,
    monthly_expense_total,
    yearly_expense_total,
)
from services.message_context import MessageContext
from services.tenant_context import TenantContext


class TestBuildInsertRow(unittest.TestCase):
    def test_builds_denormalized_l2_row_for_legacy_l3_code(self):
        context = MessageContext(tenant=TenantContext.personal('u1'), source_message_id='m1')
        row = build_insert_row(
            context=context,
            item={'description': 'Coffee', 'amount': 450, 'currency': 'JPY'},
            line_item_index=0,
            category_code='food.dining.cafe',
        )
        self.assertEqual(row.assigned_level, 2)
        self.assertIsNone(row.category_l3_id)
        self.assertEqual(row.currency, 'JPY')
        self.assertEqual(row.amount, Decimal('450.00'))


class TestInsertExpenses(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(os.environ, {}, clear=False)
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    @patch('services.expense_repository.is_supabase_configured', return_value=False)
    def test_skips_when_not_configured(self, _configured):
        row = ExpenseInsertRow(
            tenant_type='user',
            tenant_id='u1',
            logged_by_line_user_id='u1',
            line_user_id='u1',
            source_message_id='m1',
            line_item_index=0,
            description='Test',
            amount=Decimal('10.00'),
            currency='JPY',
            expense_date=date.today(),
            category_node_id='x',
            assigned_level=1,
            category_l1_id='x',
            category_l2_id=None,
            category_l3_id=None,
        )
        result = insert_expenses([row])
        self.assertEqual(result, PersistResult(inserted=0, skipped=0))

    @patch('services.expense_repository._count_existing_rows', return_value=0)
    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_insert_success(self, _configured, get_client, _count):
        table = MagicMock()
        upsert = MagicMock()
        upsert.execute.return_value = MagicMock(data=[{'id': '1'}])
        table.upsert.return_value = upsert
        client = MagicMock()
        client.table.return_value = table
        get_client.return_value = client

        row = ExpenseInsertRow(
            tenant_type='user',
            tenant_id='u1',
            logged_by_line_user_id='u1',
            line_user_id='u1',
            source_message_id='m1',
            line_item_index=0,
            description='Test',
            amount=Decimal('10.00'),
            currency='JPY',
            expense_date=date.today(),
            category_node_id='x',
            assigned_level=1,
            category_l1_id='x',
            category_l2_id=None,
            category_l3_id=None,
        )
        result = insert_expenses([row])
        self.assertEqual(result.inserted, 1)
        self.assertIsNone(result.error)
        table.upsert.assert_called_once()
        kwargs = table.upsert.call_args.kwargs
        self.assertTrue(kwargs.get('ignore_duplicates'))

    @patch('services.expense_repository.get_supabase_client', side_effect=RuntimeError('db down'))
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_insert_error_does_not_raise(self, _configured, _client):
        row = ExpenseInsertRow(
            tenant_type='user',
            tenant_id='u1',
            logged_by_line_user_id='u1',
            line_user_id='u1',
            source_message_id='m1',
            line_item_index=0,
            description='Test',
            amount=Decimal('10.00'),
            currency='JPY',
            expense_date=date.today(),
            category_node_id='x',
            assigned_level=1,
            category_l1_id='x',
            category_l2_id=None,
            category_l3_id=None,
        )
        result = insert_expenses([row])
        self.assertEqual(result.inserted, 0)
        self.assertIsNotNone(result.error)


class TestRollupRpc(unittest.TestCase):
    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_monthly_rpc(self, _configured, get_client):
        rpc = MagicMock()
        rpc.execute.return_value = MagicMock(data=1234.5)
        client = MagicMock()
        client.rpc.return_value = rpc
        get_client.return_value = client

        tenant = TenantContext.personal('u1')
        total = monthly_expense_total(tenant, 2026, 6, 'cat-id', 'JPY')
        self.assertEqual(total, Decimal('1234.5'))
        client.rpc.assert_called_once_with(
            'monthly_expense_total',
            {
                'p_tenant_type': 'user',
                'p_tenant_id': 'u1',
                'p_year': 2026,
                'p_month': 6,
                'p_category_node_id': 'cat-id',
                'p_currency': 'JPY',
            },
        )

    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_yearly_rpc(self, _configured, get_client):
        rpc = MagicMock()
        rpc.execute.return_value = MagicMock(data=9999)
        client = MagicMock()
        client.rpc.return_value = rpc
        get_client.return_value = client

        total = yearly_expense_total(TenantContext.personal('u1'), 2026, 'cat-id', 'JPY')
        self.assertEqual(total, Decimal('9999'))


if __name__ == '__main__':
    unittest.main()
