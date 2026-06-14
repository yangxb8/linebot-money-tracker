import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from services.confirmation_repository import ConfirmationRecord
from services.tenant_context import TenantContext
from services.expense_repository import ExpenseRow, UpdateResult
from services.gemini_client import GeminiClient
from services.message_handler import format_expense_items
from services.reply_edit import (
    _amount_correction_intent,
    _bare_number_intent,
    _category_bulk_intent,
    _delete_phrase_intent,
    _item_prefixed_intent,
    _parse_item_number_tokens,
    apply_edit_intent,
    is_affirmative,
    is_cancel_pending,
    parse_edit_intent,
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

    def test_validate_edit_intent_coerces_amount_string(self):
        items = [{'line_item_index': 0, 'expense_id': 'e1'}]
        intent = {
            'action': 'update',
            'target': {'mode': 'unspecified'},
            'updates': {'amount': '1700'},
        }
        parsed = validate_edit_intent(intent, items)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['updates']['amount'], 1700.0)
        self.assertEqual(parsed['target']['mode'], 'single')
        self.assertEqual(parsed['target']['line_item_index'], 0)

    def test_amount_correction_intent_japanese_typo(self):
        items = [{'line_item_index': 0, 'expense_id': 'e1', 'currency': 'JPY'}]
        intent = _amount_correction_intent('打错了，1700', items)
        self.assertIsNotNone(intent)
        self.assertEqual(intent['action'], 'update')
        self.assertEqual(intent['updates']['amount'], 1700.0)

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

    def test_item_prefixed_amount_update(self):
        items = [
            {'line_item_index': 0, 'expense_id': 'e1'},
            {'line_item_index': 1, 'expense_id': 'e2'},
        ]
        intent = _item_prefixed_intent('2 3800円', items)
        self.assertIsNotNone(intent)
        self.assertEqual(intent['action'], 'update')
        self.assertEqual(intent['target']['line_item_index'], 1)
        self.assertEqual(intent['updates']['amount'], 3800.0)

    def test_item_prefixed_category_pick(self):
        items = [
            {'line_item_index': 0, 'category_alternatives': ['a']},
            {'line_item_index': 1, 'category_alternatives': ['b', 'c']},
        ]
        intent = _item_prefixed_intent('2 1', items)
        self.assertEqual(intent['target']['line_item_index'], 1)
        self.assertEqual(intent['updates']['category_alternative_number'], 1)

    def test_item_prefixed_delete(self):
        items = [
            {'line_item_index': 0, 'expense_id': 'e1'},
            {'line_item_index': 1, 'expense_id': 'e2'},
        ]
        intent = _item_prefixed_intent('2 取消', items)
        self.assertEqual(intent['action'], 'soft_delete')
        self.assertEqual(intent['target']['line_item_index'], 1)

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

    def test_is_cancel_pending(self):
        self.assertTrue(is_cancel_pending('cancel'))
        self.assertTrue(is_cancel_pending('いいえ'))
        self.assertFalse(is_cancel_pending('delete'))

    def test_delete_phrase_single_item(self):
        items = [{'line_item_index': 0, 'expense_id': 'e1', 'description': 'Coffee'}]
        for phrase in ('cancel', 'delete', 'キャンセル', '删除'):
            with self.subTest(phrase=phrase):
                intent = _delete_phrase_intent(phrase, items)
                self.assertIsNotNone(intent)
                self.assertEqual(intent['action'], 'soft_delete')
                self.assertEqual(intent['target']['mode'], 'single')

    def test_delete_phrase_multi_item_triggers_delete_all(self):
        items = [
            {'line_item_index': 0, 'expense_id': 'e1'},
            {'line_item_index': 1, 'expense_id': 'e2'},
        ]
        for phrase in ('cancel', '取消', '删除'):
            with self.subTest(phrase=phrase):
                intent = _delete_phrase_intent(phrase, items)
                self.assertEqual(intent['action'], 'soft_delete_all')
                self.assertEqual(intent['target']['mode'], 'all_active')

    def test_delete_all_phrases_chinese(self):
        items = [{'line_item_index': 0, 'expense_id': 'e1'}]
        for phrase in ('全部取消', '全部删除', '取消全部', 'delete all'):
            with self.subTest(phrase=phrase):
                intent = _delete_phrase_intent(phrase, items)
                self.assertEqual(intent['action'], 'soft_delete_all')

    def test_cancel_pending_includes_chinese_quxiao(self):
        self.assertTrue(is_cancel_pending('取消'))

    def test_delete_phrase_non_delete(self):
        items = [{'line_item_index': 0, 'expense_id': 'e1'}]
        self.assertIsNone(_delete_phrase_intent('3800円', items))

    def test_parse_item_number_tokens(self):
        self.assertEqual(_parse_item_number_tokens('1 3'), [1, 3])
        self.assertEqual(_parse_item_number_tokens('1,3'), [1, 3])
        self.assertEqual(_parse_item_number_tokens('2'), [2])

    def test_category_bulk_single_item(self):
        items = [{'line_item_index': 0, 'expense_id': 'e1'}]
        intent = _category_bulk_intent('餐饮', items)
        self.assertIsNotNone(intent)
        self.assertEqual(intent['action'], 'category_bulk')
        self.assertEqual(intent['updates']['category_query'], '餐饮')
        self.assertTrue(intent.get('skip_intent_confirm'))

    def test_category_bulk_subset_space(self):
        items = [
            {'line_item_index': 0, 'expense_id': 'e1'},
            {'line_item_index': 1, 'expense_id': 'e2'},
            {'line_item_index': 2, 'expense_id': 'e3'},
        ]
        intent = _category_bulk_intent('1 3 交通', items)
        self.assertEqual(intent['action'], 'category_bulk')
        self.assertEqual(intent['target']['mode'], 'subset')
        self.assertEqual(intent['target']['line_item_indices'], [0, 2])

    def test_category_bulk_subset_comma(self):
        items = [
            {'line_item_index': 0, 'expense_id': 'e1'},
            {'line_item_index': 1, 'expense_id': 'e2'},
        ]
        intent = _category_bulk_intent('1,2 食品', items)
        self.assertEqual(intent['target']['line_item_indices'], [0, 1])

    def test_category_bulk_multi_item_bare_returns_none(self):
        items = [
            {'line_item_index': 0, 'expense_id': 'e1'},
            {'line_item_index': 1, 'expense_id': 'e2'},
        ]
        self.assertIsNone(_category_bulk_intent('餐饮', items))


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


class TestParseEditIntent(unittest.IsolatedAsyncioTestCase):
    async def test_parse_edit_intent_uses_llm_for_amount_correction(self):
        items = [{'line_item_index': 0, 'expense_id': 'e1', 'description': 'Coffee', 'amount': 1500}]
        gemini = MagicMock(spec=GeminiClient)
        gemini.generate_json_reply = AsyncMock(
            return_value=(
                '{"action":"update","target":{"mode":"single","line_item_index":0},'
                '"updates":{"amount":1700},"clarification_needed":false,"clarification_message":null}'
            )
        )
        intent = await parse_edit_intent('打错了，1700', items, None, gemini)
        self.assertEqual(intent['action'], 'update')
        self.assertEqual(intent['updates']['amount'], 1700)
        gemini.generate_json_reply.assert_awaited_once()

    async def test_parse_edit_intent_falls_back_to_amount_extractor(self):
        items = [{'line_item_index': 0, 'expense_id': 'e1', 'description': 'Coffee', 'amount': 1500}]
        gemini = MagicMock(spec=GeminiClient)
        gemini.generate_json_reply = AsyncMock(side_effect=RuntimeError('api down'))
        intent = await parse_edit_intent('打错了，1700', items, None, gemini)
        self.assertEqual(intent['action'], 'update')
        self.assertEqual(intent['updates']['amount'], 1700.0)


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
            tenant=TenantContext.personal('u1'),
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
        gemini = MagicMock(spec=GeminiClient)
        result = await apply_edit_intent(intent, confirmation, '1', gemini)
        self.assertEqual(result.status, 'applied')
        update_fields.assert_called_once()

    @patch('services.reply_edit.update_items_snapshot')
    @patch('services.reply_edit.get_expenses_by_ids')
    @patch('services.reply_edit.soft_delete_expenses')
    async def test_apply_cancel_soft_deletes_single_item(self, soft_delete, get_by_ids, _update_snap):
        soft_delete.return_value = __import__(
            'services.expense_repository', fromlist=['MutationResult']
        ).MutationResult(success=True, affected=1)
        expense_row = ExpenseRow(
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
        get_by_ids.return_value = [expense_row]
        confirmation = ConfirmationRecord(
            id='c1',
            bot_message_id='bot-1',
            tenant=TenantContext.personal('u1'),
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
        intent = _delete_phrase_intent('cancel', list(confirmation.items_snapshot))
        gemini = MagicMock(spec=GeminiClient)
        result = await apply_edit_intent(intent, confirmation, 'cancel', gemini)
        self.assertEqual(result.status, 'applied')
        self.assertIn('Soft-deleted', result.summary)
        soft_delete.assert_called_once_with(['e1'])

    @patch('services.reply_edit.update_items_snapshot')
    @patch('services.reply_edit.get_expenses_by_ids')
    @patch('services.reply_edit.update_expense_fields')
    async def test_apply_amount_correction(self, update_fields, get_by_ids, _update_snap):
        update_fields.return_value = UpdateResult(success=True)
        expense_row_before = ExpenseRow(
            id='e1',
            line_user_id='u1',
            description='Coffee',
            amount=Decimal('1500'),
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
            amount=Decimal('1700'),
            currency='JPY',
            expense_date=__import__('datetime').date.today(),
            category_node_id='old',
            assigned_level=1,
            category_l1_id='old',
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
            tenant=TenantContext.personal('u1'),
            confirmation_text='text',
            items_snapshot=(
                {
                    'line_item_index': 0,
                    'expense_id': 'e1',
                    'description': 'Coffee',
                    'amount': 1500,
                    'currency': 'JPY',
                    'category_guess_code': 'food.dining.cafe',
                    'category_alternatives': ['food.grocery', 'unknown'],
                },
            ),
            pending_action=None,
        )
        intent = _amount_correction_intent('打错了，1700', list(confirmation.items_snapshot))
        gemini = MagicMock(spec=GeminiClient)
        result = await apply_edit_intent(intent, confirmation, '打错了，1700', gemini)
        self.assertEqual(result.status, 'applied')
        update_fields.assert_called_once()
        self.assertEqual(update_fields.call_args.kwargs['amount'], Decimal('1700.00'))

    @patch('services.reply_edit.clear_pending_state')
    @patch('services.reply_edit.update_items_snapshot')
    @patch('services.reply_edit.get_expenses_by_ids')
    @patch('services.reply_edit.update_expense_fields')
    @patch('services.reply_edit.set_pending_state')
    @patch('services.reply_edit.map_category_from_text', new_callable=AsyncMock)
    async def test_apply_category_bulk_single_item(
        self,
        map_category,
        set_pending,
        update_fields,
        get_by_ids,
        _update_snap,
        _clear_pending,
    ):
        map_category.return_value = ('food.dining.restaurant', 'food.dining.cafe')
        update_fields.return_value = UpdateResult(success=True)
        expense_row = ExpenseRow(
            id='e1',
            line_user_id='u1',
            description='Lunch',
            amount=Decimal('1000'),
            currency='JPY',
            expense_date=__import__('datetime').date.today(),
            category_node_id='old',
            assigned_level=1,
            category_l1_id='old',
            category_l2_id=None,
            category_l3_id=None,
        )
        get_by_ids.return_value = [expense_row]
        confirmation = ConfirmationRecord(
            id='c1',
            bot_message_id='bot-1',
            tenant=TenantContext.personal('u1'),
            confirmation_text='text',
            items_snapshot=(
                {
                    'line_item_index': 0,
                    'expense_id': 'e1',
                    'description': 'Lunch',
                    'amount': 1000,
                    'currency': 'JPY',
                    'category_guess_code': 'food.dining.cafe',
                    'category_alternatives': ['food.grocery'],
                },
            ),
            pending_action=None,
        )
        intent = _category_bulk_intent('餐饮', list(confirmation.items_snapshot))
        gemini = MagicMock(spec=GeminiClient)
        result = await apply_edit_intent(intent, confirmation, '餐饮', gemini)
        self.assertEqual(result.status, 'applied')
        self.assertIn('1)', result.summary)
        set_pending.assert_called_once()
        map_category.assert_awaited_once()

    @patch('services.reply_edit.clear_pending_state')
    @patch('services.reply_edit.update_items_snapshot')
    @patch('services.reply_edit.get_expenses_by_ids')
    @patch('services.reply_edit.update_expense_fields')
    async def test_apply_category_bulk_pick(
        self,
        update_fields,
        get_by_ids,
        _update_snap,
        _clear_pending,
    ):
        update_fields.return_value = UpdateResult(success=True)
        expense_rows = [
            ExpenseRow(
                id='e1',
                line_user_id='u1',
                description='A',
                amount=Decimal('100'),
                currency='JPY',
                expense_date=__import__('datetime').date.today(),
                category_node_id='old',
                assigned_level=1,
                category_l1_id='old',
                category_l2_id=None,
                category_l3_id=None,
            ),
            ExpenseRow(
                id='e2',
                line_user_id='u1',
                description='B',
                amount=Decimal('200'),
                currency='JPY',
                expense_date=__import__('datetime').date.today(),
                category_node_id='old',
                assigned_level=1,
                category_l1_id='old',
                category_l2_id=None,
                category_l3_id=None,
            ),
        ]
        get_by_ids.return_value = expense_rows
        confirmation = ConfirmationRecord(
            id='c1',
            bot_message_id='bot-1',
            tenant=TenantContext.personal('u1'),
            confirmation_text='text',
            items_snapshot=(
                {
                    'line_item_index': 0,
                    'expense_id': 'e1',
                    'description': 'A',
                    'amount': 100,
                    'currency': 'JPY',
                    'category_guess_code': 'food.dining.cafe',
                    'category_alternatives': [],
                },
                {
                    'line_item_index': 1,
                    'expense_id': 'e2',
                    'description': 'B',
                    'amount': 200,
                    'currency': 'JPY',
                    'category_guess_code': 'food.dining.cafe',
                    'category_alternatives': [],
                },
            ),
            pending_action='category_bulk',
            pending_payload={
                'category_query': '餐饮',
                'category_options': ['food.dining.restaurant', 'food.dining.cafe'],
                'target_line_item_indices': [0, 1],
            },
        )
        intent = {
            'action': 'confirm_pending',
            'target': {'mode': 'unspecified'},
            'updates': {'category_alternative_number': 1},
        }
        gemini = MagicMock(spec=GeminiClient)
        result = await apply_edit_intent(intent, confirmation, '1', gemini)
        self.assertEqual(result.status, 'applied')
        self.assertEqual(update_fields.call_count, 2)
        _clear_pending.assert_called_once()


if __name__ == '__main__':
    unittest.main()
