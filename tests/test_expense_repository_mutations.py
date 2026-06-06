import os
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services.expense_repository import (
    ExpenseRow,
    MutationResult,
    UpdateResult,
    get_expenses_by_ids,
    restore_expenses,
    soft_delete_expenses,
    update_expense_fields,
)


class TestExpenseRepositoryMutations(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(os.environ, {}, clear=False)
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    @patch('services.expense_repository.is_supabase_configured', return_value=False)
    def test_update_skips_when_not_configured(self, _configured):
        result = update_expense_fields('id-1', description='New')
        self.assertFalse(result.success)

    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_update_expense_fields(self, _configured, get_client):
        table = MagicMock()
        update_chain = MagicMock()
        update_chain.eq.return_value = update_chain
        update_chain.execute.return_value = MagicMock(data=[{'id': 'id-1'}])
        table.update.return_value = update_chain
        client = MagicMock()
        client.table.return_value = table
        get_client.return_value = client

        result = update_expense_fields(
            'id-1',
            description='Updated',
            amount=Decimal('100.00'),
            category_code='unknown',
        )
        self.assertTrue(result.success)
        table.update.assert_called_once()

    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_soft_delete_expenses(self, _configured, get_client):
        table = MagicMock()
        chain = MagicMock()
        chain.is_.return_value = chain
        chain.execute.return_value = MagicMock(data=[{'id': '1'}])
        table.update.return_value.in_.return_value = chain
        client = MagicMock()
        client.table.return_value = table
        get_client.return_value = client

        result = soft_delete_expenses(['id-1'])
        self.assertIsInstance(result, MutationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.affected, 1)

    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_restore_expenses(self, _configured, get_client):
        table = MagicMock()
        chain = MagicMock()
        chain.not_.is_.return_value = chain
        chain.execute.return_value = MagicMock(data=[{'id': '1'}])
        table.update.return_value.in_.return_value = chain
        client = MagicMock()
        client.table.return_value = table
        get_client.return_value = client

        result = restore_expenses(['id-1'])
        self.assertTrue(result.success)

    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_get_expenses_by_ids(self, _configured, get_client):
        table = MagicMock()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(
            data=[
                {
                    'id': 'id-1',
                    'line_user_id': 'u1',
                    'description': 'Coffee',
                    'amount': 450,
                    'currency': 'JPY',
                    'expense_date': '2026-06-06',
                    'category_node_id': 'x',
                    'assigned_level': 1,
                    'category_l1_id': 'x',
                    'category_l2_id': None,
                    'category_l3_id': None,
                    'deleted_at': None,
                }
            ]
        )
        table.select.return_value.in_.return_value = chain
        client = MagicMock()
        client.table.return_value = table
        get_client.return_value = client

        rows = get_expenses_by_ids(['id-1'])
        self.assertEqual(len(rows), 1)
        self.assertIsInstance(rows[0], ExpenseRow)
        self.assertEqual(rows[0].description, 'Coffee')
        self.assertEqual(rows[0].expense_date, date(2026, 6, 6))


if __name__ == '__main__':
    unittest.main()
