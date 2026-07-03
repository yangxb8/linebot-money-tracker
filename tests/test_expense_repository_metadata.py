import unittest

from services.expense_repository import build_insert_row
from services.message_context import MessageContext
from services.tenant_context import TenantContext


class TestExpenseRepositoryMetadata(unittest.TestCase):
    def test_build_insert_row_includes_store_name_metadata(self):
        context = MessageContext(
            tenant=TenantContext.personal('u1'),
            source_message_id='msg-1',
            reply_language='ja',
        )
        row = build_insert_row(
            context=context,
            item={
                'description': '牛乳',
                'amount': 198,
                'currency': 'JPY',
                'store_name': 'イオン',
            },
            line_item_index=0,
            category_code='food.grocery',
        )
        self.assertEqual(row.metadata, {'store_name': 'イオン'})

    def test_build_insert_row_includes_merchant_metadata(self):
        context = MessageContext(
            tenant=TenantContext.personal('u1'),
            source_message_id='msg-1',
            reply_language='ja',
        )
        row = build_insert_row(
            context=context,
            item={
                'description': 'ラテ',
                'amount': 450,
                'currency': 'JPY',
                'store_name': 'スターバックス 渋谷店',
            },
            line_item_index=0,
            category_code='food.dining',
            merchant_key='starbucks',
            display_merchant='スターバックス',
        )
        self.assertEqual(
            row.metadata,
            {
                'store_name': 'スターバックス 渋谷店',
                'merchant_key': 'starbucks',
                'display_merchant': 'スターバックス',
            },
        )

    def test_build_insert_row_empty_metadata_without_store_name(self):
        context = MessageContext(
            tenant=TenantContext.personal('u1'),
            source_message_id='msg-1',
            reply_language='ja',
        )
        row = build_insert_row(
            context=context,
            item={'description': 'Coffee', 'amount': 450, 'currency': 'JPY'},
            line_item_index=0,
            category_code='unknown',
        )
        self.assertEqual(row.metadata, {})


if __name__ == '__main__':
    unittest.main()
