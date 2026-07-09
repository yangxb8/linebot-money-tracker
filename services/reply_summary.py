from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from services.category_taxonomy import format_category_path, resolve_code
from services.confirmation_i18n import t
from services.tenant_context import TenantContext

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

    if summary.action == 'confirm_intent_pending':
        return summary.clarification_message or _applied_generic(language)

    if summary.action == 'category_bulk_pending':
        return summary.clarification_message or _applied_generic(language)

    if summary.action == 'category_bulk':
        return _bulk_category_message(language, summary.affected_count, summary.changes)

    if summary.action in ('soft_delete', 'soft_delete_all'):
        return _delete_message(language, summary.item_description, summary.affected_count)

    if summary.action in ('restore', 'restore_all'):
        return _restore_message(language, summary.item_description, summary.affected_count)

    if summary.changes:
        return _update_message(language, summary.item_description, summary.changes)

    return _applied_generic(language)


def _error_message(language: str, detail: Optional[str]) -> str:
    fallback = {
        'zh': '请稍后再试。',
        'en': 'Please try again in a moment.',
        'ja': 'しばらくしてからもう一度お試しください。',
    }
    lang = language if language in fallback else 'ja'
    return t(language, 'edit_error', detail=detail or fallback[lang])


def _no_op_message(language: str, action: str) -> str:
    if action == 'restore':
        return t(language, 'edit_no_op_restore')
    return t(language, 'edit_no_op')


def _delete_all_prompt(language: str) -> str:
    return t(language, 'delete_all_prompt')


def _delete_message(language: str, item: Optional[str], count: int) -> str:
    if count > 1:
        return t(language, 'delete_many', count=str(count))
    label = item or 'expense'
    return t(language, 'delete_one', label=label)


def _restore_message(language: str, item: Optional[str], count: int) -> str:
    if count > 1:
        return t(language, 'restore_many', count=str(count))
    label = item or 'expense'
    return t(language, 'restore_one', label=label)


def _update_message(language: str, item: Optional[str], changes: tuple[FieldChange, ...]) -> str:
    lines: List[str] = []
    header = t(language, 'update_header', item=item) if item else t(language, 'update_header_plain')
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
    return t(language, 'applied_generic')


def format_unknown_confirmation(language: str) -> str:
    return t(language, 'unknown_confirmation')


def format_duplicate_reply(language: str) -> str:
    return t(language, 'duplicate_reply')


def category_path_for_code(code: str, tenant: Optional[TenantContext] = None) -> str:
    try:
        return format_category_path(resolve_code(code, tenant))
    except Exception:
        return code


def _bulk_category_message(language: str, count: int, changes: tuple[FieldChange, ...]) -> str:
    category_after = changes[0].after if changes else ''
    return t(language, 'bulk_category', count=str(count), category=category_after)


def format_intent_confirmation_prompt(
    language: str,
    interpretation: str,
) -> str:
    return f'{interpretation}\n\n{t(language, "intent_confirm_suffix")}'


def format_category_guess_confirmation(
    language: str,
    guessed_category_path: str,
) -> str:
    if language == 'zh':
        return f'类别是「{guessed_category_path}」吗？回复 YES 确认。'
    if language == 'en':
        return f'Category: "{guessed_category_path}" — reply YES to confirm.'
    return f'カテゴリは「{guessed_category_path}」でOK？ YES で確定'


def format_category_options_prompt(
    language: str,
    category_query: str,
    option_codes: tuple[str, ...],
    item_labels: tuple[str, ...] = (),
    tenant: Optional[TenantContext] = None,
) -> str:
    lines: List[str] = []
    if item_labels:
        labels = ', '.join(item_labels)
        lines.append(
            t(language, 'category_pick_header_items', labels=labels, query=category_query)
        )
    else:
        lines.append(t(language, 'category_pick_header', query=category_query))

    for index, code in enumerate(option_codes, start=1):
        path = category_path_for_code(code, tenant)
        lines.append(f'{index}) {path}')

    lines.append(t(language, 'category_pick_footer'))
    return '\n'.join(lines)


def describe_category_bulk_intent(
    language: str,
    category_query: str,
    target_labels: tuple[str, ...],
    all_items: bool,
) -> str:
    if all_items:
        return t(language, 'category_bulk_all', category_query=category_query)

    labels = ', '.join(target_labels)
    return t(language, 'category_bulk_items', labels=labels, category_query=category_query)


def format_amount(amount: Decimal, currency: str) -> str:
    return f'{amount} {currency}'
