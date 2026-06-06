import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from services.confirmation_repository import ConfirmationRecord
from services.expense_repository import ExpenseRow, UpdateResult
from services.gemini_client import GeminiClient
from services.message_handler import format_expense_items
from services.reply_edit import (
    _bare_number_intent,
    is_affirmative,
    resolve_category_pick,
    validate_edit_intent,
)
from services.reply_summary import EditSummaryInput, detect_reply_language, format_edit_result


class TestReplyEditIntent(unittest.TestCase):
    def test_validate_edit_intent_accepts_update(self):
        intent = {
            'action': 'update',
            'target': {'mode': 'single', 'line_item_index': 0},
            'updates': {'amount': 100},
        }
        self.assertIsNotNone(validate_edit_intent(intent))

    def test_bare_number_single_item(self):
        items = [{'line_item_index': 0, 'category_alternatives': ['a', 'b']}]
        intent = _bare_number_intent('2', items)
        self.assertEqual(intent['action'], 'update')
        self.assertEqual(intent['updates']['category_alternative_number'], 2)

    def test_bare_number_multi_item_clarifies(self):
        items = [
            {'line_item_index': 0, 'category_alternatives': ['a']},
            {'line_item_index': 1, 'category_alternatives': ['b']},
        ]
        intent = _bare_number_intent('2', items)
        self.assertEqual(intent['action'], 'clarify')

    def test_resolve_category_pick_single(self):
        items = [
            {
                'line_item_index': 0,
                'category_alternatives': ['food.grocery', 'unknown', 'food.dining'],
            }
        ]
        intent = {
            'action': 'update',
            'target': {'mode': 'single', 'line_item_index': 0},
            'updates': {'category_alternative_number': 2},
        }
        code, err = resolve_category_pick(intent, items)
        self.assertEqual(code, 'unknown')
        self.assertIsNone(err)

    def test_is_affirmative(self):
        self.assertTrue(is_affirmative('YES'))
        self.assertTrue(is_affirmative('はい'))
        self.assertFalse(is_affirmative('maybe'))


class TestReplySummary(unittest.TestCase):
    def test_detect_japanese(self):
        self.assertEqual(detect_reply_language('3800円に修正'), 'ja')

    def test_detect_english(self):
        self.assertEqual(detect_reply_language('change amount to 100'), 'en')

    def test_format_category_update_japanese(self):
        summary = format_edit_result(
            'ja',
            EditSummaryInput(
                status='applied',
                action='update',
                item_description='Coffee',
                changes=(
                    __import__('services.reply_summary', fromlist=['FieldChange']).FieldChange(
                        'category', '食費 > 外食', '食費 > 食料品'
                    ),
                ),
            ),
        )
        self.assertIn('更新しました', summary)
        self.assertIn('→', summary)


class TestReplyEditApply(unittest.IsolatedAsyncioTestCase):
    @patch('services.reply_edit.update_items_snapshot')
    @patch('services.reply_edit.get_expenses_by_ids')
    @patch('services.reply_edit.update_expense_fields')
    async def test_apply_category_update(self, update_fields, get_by_ids, _update_snap):
        update_fields.return_value = UpdateResult(success=True)
        expense_row_before = ExpenseRow(
            id='e1',
            line_user_id='u1',
            description='Coffee',
            amount=Decimal('450'),
            currency='JPY',
            expense_date=__import__('datetime').date.today(),
            category_node_id='old',
            assigned_level=1,
            category_l1_id='old',
            category_l2_id=None,
            category_l3_id=None,
        )
        expense_row_after = ExpenseRow(
            id='e1',
            line_user_id='u1',
            description='Coffee',
            amount=Decimal('450'),
            currency='JPY',
            expense_date=__import__('datetime').date.today(),
            category_node_id='new',
            assigned_level=1,
            category_l1_id='new',
            category_l2_id=None,
            category_l3_id=None,
        )
        get_by_ids.side_effect = [
            [expense_row_before],
            [expense_row_before],
            [expense_row_after],
        ]
        confirmation = ConfirmationRecord(
            id='c1',
            bot_message_id='bot-1',
            line_user_id='u1',
            confirmation_text='text',
            items_snapshot=(
                {
                    'line_item_index': 0,
                    'expense_id': 'e1',
                    'description': 'Coffee',
                    'amount': 450,
                    'currency': 'JPY',
                    'category_guess_code': 'food.dining.cafe',
                    'category_alternatives': ['food.grocery', 'unknown'],
                },
            ),
            pending_action=None,
        )
        intent = {
            'action': 'update',
            'target': {'mode': 'single', 'line_item_index': 0},
            'updates': {'category_alternative_number': 1},
        }
        from services.reply_edit import apply_edit_intent

        gemini = MagicMock(spec=GeminiClient)
        result = await apply_edit_intent(intent, confirmation, '1', gemini)
        self.assertEqual(result.status, 'applied')
        update_fields.assert_called_once()


if __name__ == '__main__':
    unittest.main()
