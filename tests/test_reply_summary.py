import unittest

from services.reply_summary import (
    EditSummaryInput,
    FieldChange,
    detect_reply_language,
    format_edit_result,
    format_unknown_confirmation,
)


class TestReplySummary(unittest.TestCase):
    def test_detect_chinese(self):
        self.assertEqual(detect_reply_language('删除全部'), 'zh')

    def test_format_delete_english(self):
        text = format_edit_result(
            'en',
            EditSummaryInput(
                status='applied',
                action='soft_delete',
                item_description='Coffee',
                affected_count=1,
            ),
        )
        self.assertIn('Soft-deleted', text)

    def test_format_delete_all_prompt_japanese(self):
        text = format_edit_result(
            'ja',
            EditSummaryInput(status='applied', action='soft_delete_all_pending'),
        )
        self.assertIn('YES', text)

    def test_format_restore_chinese(self):
        text = format_edit_result(
            'zh',
            EditSummaryInput(status='applied', action='restore_all', affected_count=2),
        )
        self.assertIn('恢复', text)

    def test_format_field_changes(self):
        text = format_edit_result(
            'en',
            EditSummaryInput(
                status='applied',
                action='update',
                item_description='Lunch',
                changes=(
                    FieldChange('amount', '100 JPY', '120 JPY'),
                ),
            ),
        )
        self.assertIn('100 JPY', text)
        self.assertIn('120 JPY', text)

    def test_unknown_confirmation_messages(self):
        self.assertIn('reply', format_unknown_confirmation('en').lower())
        self.assertIn('返信', format_unknown_confirmation('ja'))

    def test_format_bulk_category_chinese(self):
        text = format_edit_result(
            'zh',
            EditSummaryInput(
                status='applied',
                action='category_bulk',
                affected_count=1,
                changes=(FieldChange('category', '', '休闲 > 游乐吃饭'),),
            ),
        )
        self.assertIn('已将', text)
        self.assertIn('类别更新为', text)
        self.assertNotIn('Updated category', text)

    def test_detect_yes_is_english_without_cjk(self):
        # Affirmative English YES has no CJK; callers must not use this alone
        # for outbound copy after a localized pending prompt.
        self.assertEqual(detect_reply_language('Yes'), 'en')


if __name__ == '__main__':
    unittest.main()
