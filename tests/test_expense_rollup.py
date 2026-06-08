import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services.category_taxonomy import category_id_for_code
from services.expense_repository import monthly_expense_total, yearly_expense_total
from services.tenant_context import TenantContext


class TestExpenseRollup(unittest.TestCase):
    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_monthly_l1_food_filter(self, _configured, get_client):
        food_id = category_id_for_code('food')
        rpc = MagicMock()
        rpc.execute.return_value = MagicMock(data=1500)
        client = MagicMock()
        client.rpc.return_value = rpc
        get_client.return_value = client

        tenant = TenantContext.personal('local-dev-user')
        total = monthly_expense_total(tenant, 2026, 6, food_id, 'JPY')
        self.assertEqual(total, Decimal('1500'))
        client.rpc.assert_called_once_with(
            'monthly_expense_total',
            {
                'p_tenant_type': 'user',
                'p_tenant_id': 'local-dev-user',
                'p_year': 2026,
                'p_month': 6,
                'p_category_node_id': food_id,
                'p_currency': 'JPY',
            },
        )

    @patch('services.expense_repository.get_supabase_client')
    @patch('services.expense_repository.is_supabase_configured', return_value=True)
    def test_yearly_l2_dining_filter(self, _configured, get_client):
        dining_id = category_id_for_code('food.dining')
        rpc = MagicMock()
        rpc.execute.return_value = MagicMock(data=800)
        client = MagicMock()
        client.rpc.return_value = rpc
        get_client.return_value = client

        total = yearly_expense_total(TenantContext.personal('local-dev-user'), 2026, dining_id, 'JPY')
        self.assertEqual(total, Decimal('800'))


if __name__ == '__main__':
    unittest.main()
