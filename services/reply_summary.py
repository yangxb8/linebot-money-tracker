from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from services.category_taxonomy import format_category_path, resolve_code

_HIRAGANA = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
_CJK = re.compile(r'[\u4e00-\u9fff]')


def detect_reply_language(text: str) -> str:
    """Return 'ja', 'zh', or 'en' using simple heuristics."""
    if not text or not text.strip():
        return 'ja'
    if _HIRAGANA.search(text):
        return 'ja'
    if _CJK.search(text):
        return 'zh'
    return 'en'


@dataclass(frozen=True)
class FieldChange:
    field: str
    before: str
    after: str


@dataclass(frozen=True)
class EditSummaryInput:
    status: str
    action: str
    changes: tuple[FieldChange, ...] = ()
    item_description: Optional[str] = None
    affected_count: int = 0
    error_message: Optional[str] = None
    clarification_message: Optional[str] = None


def format_edit_result(language: str, summary: EditSummaryInput) -> str:
    if summary.clarification_message:
        return summary.clarification_message

    if summary.status == 'error':
        return _error_message(language, summary.error_message)

    if summary.status == 'no_op':
        return _no_op_message(language, summary.action)

    if summary.action == 'soft_delete_all_pending':
        return _delete_all_prompt(language)

    if summary.action in ('soft_delete', 'soft_delete_all'):
        return _delete_message(language, summary.item_description, summary.affected_count)

    if summary.action in ('restore', 'restore_all'):
        return _restore_message(language, summary.item_description, summary.affected_count)

    if summary.changes:
        return _update_message(language, summary.item_description, summary.changes)

    return _applied_generic(language)


def _error_message(language: str, detail: Optional[str]) -> str:
    if language == 'zh':
        return f'无法保存更改。{detail or "请稍后再试。"}'
    if language == 'en':
        return f"Couldn't save your changes. {detail or 'Please try again in a moment.'}"
    return f'変更を保存できませんでした。{detail or "しばらくしてからもう一度お試しください。"}'


def _no_op_message(language: str, action: str) -> str:
    if action == 'restore':
        if language == 'zh':
            return '没有可恢复的记录（可能已经是有效状态）。'
        if language == 'en':
            return 'Nothing to restore — the expense may already be active.'
        return '復元する項目がありません（すでに有効な可能性があります）。'
    if language == 'zh':
        return '没有进行任何更改。'
    if language == 'en':
        return 'No changes were made.'
    return '変更はありませんでした。'


def _delete_all_prompt(language: str) -> str:
    if language == 'zh':
        return '将软删除此确认中的所有支出。回复 YES 确认。'
    if language == 'en':
        return 'This will soft-delete all expenses on this confirmation. Reply YES to confirm.'
    return 'この確認の支出をすべて削除します。YES と返信して確定してください。'


def _delete_message(language: str, item: Optional[str], count: int) -> str:
    if count > 1:
        if language == 'zh':
            return f'已软删除 {count} 笔支出。'
        if language == 'en':
            return f'Soft-deleted {count} expense(s).'
        return f'{count} 件の支出を削除しました。'
    label = item or 'expense'
    if language == 'zh':
        return f'已软删除：{label}'
    if language == 'en':
        return f'Soft-deleted: {label}'
    return f'削除しました：{label}'


def _restore_message(language: str, item: Optional[str], count: int) -> str:
    if count > 1:
        if language == 'zh':
            return f'已恢复 {count} 笔支出。'
        if language == 'en':
            return f'Restored {count} expense(s).'
        return f'{count} 件の支出を復元しました。'
    label = item or 'expense'
    if language == 'zh':
        return f'已恢复：{label}'
    if language == 'en':
        return f'Restored: {label}'
    return f'復元しました：{label}'


def _update_message(language: str, item: Optional[str], changes: tuple[FieldChange, ...]) -> str:
    lines: List[str] = []
    if language == 'zh':
        header = f'已更新：{item}' if item else '已更新'
    elif language == 'en':
        header = f'Updated: {item}' if item else 'Updated'
    else:
        header = f'更新しました：{item}' if item else '更新しました'
    lines.append(header)

    for change in changes:
        if language == 'zh':
            lines.append(f'  {change.field}：{change.before} → {change.after}')
        elif language == 'en':
            lines.append(f'  {change.field}: {change.before} → {change.after}')
        else:
            lines.append(f'  {change.field}：{change.before} → {change.after}')

    return '\n'.join(lines)


def _applied_generic(language: str) -> str:
    if language == 'zh':
        return '已应用更改。'
    if language == 'en':
        return 'Changes applied.'
    return '変更を反映しました。'


def format_unknown_confirmation(language: str) -> str:
    if language == 'zh':
        return '请回复机器人发送的支出确认消息以进行编辑。'
    if language == 'en':
        return 'Please reply to the bot expense confirmation message to make edits.'
    return '編集するには、ボットの支出確認メッセージに返信してください。'


def format_duplicate_reply(language: str) -> str:
    if language == 'zh':
        return '此回复已处理过。'
    if language == 'en':
        return 'This reply was already processed.'
    return 'この返信はすでに処理済みです。'


def category_path_for_code(code: str) -> str:
    try:
        return format_category_path(resolve_code(code))
    except Exception:
        return code


def format_amount(amount: Decimal, currency: str) -> str:
    return f'{amount} {currency}'
