from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft7Validator, ValidationError

from services.confirmation_repository import ConfirmationRecord, set_pending_action, update_items_snapshot
from services.expense_repository import (
    ExpenseRow,
    get_expenses_by_ids,
    restore_expenses,
    soft_delete_expenses,
    update_expense_fields,
)
from services.gemini_client import GeminiClient
from services.reply_summary import (
    EditSummaryInput,
    FieldChange,
    category_path_for_code,
    detect_reply_language,
    format_amount,
    format_edit_result,
)

logger = logging.getLogger(__name__)

EDIT_INTENT_SCHEMA: Dict[str, Any] = {
    'type': 'object',
    'required': ['action'],
    'properties': {
        'action': {
            'type': 'string',
            'enum': [
                'update',
                'soft_delete',
                'soft_delete_all',
                'restore',
                'restore_all',
                'confirm_pending',
                'clarify',
            ],
        },
        'target': {
            'type': 'object',
            'properties': {
                'mode': {
                    'type': 'string',
                    'enum': ['single', 'all_active', 'all_deleted', 'unspecified'],
                },
                'line_item_index': {'type': 'integer', 'minimum': 0},
                'description_hint': {'type': 'string'},
            },
            'additionalProperties': True,
        },
        'updates': {
            'type': 'object',
            'properties': {
                'amount': {'type': 'number', 'exclusiveMinimum': 0},
                'currency': {'type': 'string', 'minLength': 3, 'maxLength': 3},
                'description': {'type': 'string', 'minLength': 1},
                'expense_date': {'type': 'string'},
                'category_code': {'type': 'string'},
                'category_alternative_number': {'type': 'integer', 'minimum': 1, 'maximum': 3},
            },
            'additionalProperties': True,
        },
        'clarification_needed': {'type': 'boolean'},
        'clarification_message': {'type': ['string', 'null']},
    },
    'additionalProperties': True,
}

_intent_validator = Draft7Validator(EDIT_INTENT_SCHEMA)
_JSON_FENCE_RE = re.compile(r'^```(?:json)?\s*(.*?)\s*```$', re.DOTALL | re.IGNORECASE)
_AFFIRMATIVE_RE = re.compile(
    r'^(yes|y|ok|confirm|はい|了解|確認|是|好|可以)$',
    re.IGNORECASE,
)


@dataclass
class EditApplyResult:
    status: str
    summary: str
    intent_json: Dict[str, Any]
    items_snapshot: List[Dict[str, Any]] = field(default_factory=list)


def is_affirmative(text: str) -> bool:
    return bool(_AFFIRMATIVE_RE.match((text or '').strip()))


def _parse_json_object(response: str) -> Any:
    text = response.strip()
    fence_match = _JSON_FENCE_RE.match(text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def validate_edit_intent(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    try:
        _intent_validator.validate(raw)
    except ValidationError:
        return None
    return raw


def _bare_number_intent(user_text: str, items_snapshot: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    stripped = user_text.strip()
    if stripped not in ('1', '2', '3'):
        return None

    if len(items_snapshot) == 1:
        return {
            'action': 'update',
            'target': {'mode': 'single', 'line_item_index': items_snapshot[0].get('line_item_index', 0)},
            'updates': {'category_alternative_number': int(stripped)},
            'clarification_needed': False,
            'clarification_message': None,
        }

    return {
        'action': 'clarify',
        'target': {'mode': 'unspecified'},
        'updates': {},
        'clarification_needed': True,
        'clarification_message': None,
    }


def resolve_category_pick(
    intent: Dict[str, Any],
    items_snapshot: List[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[str]]:
    updates = intent.get('updates') or {}
    alt_num = updates.get('category_alternative_number')
    if alt_num is None:
        code = updates.get('category_code')
        if code:
            return str(code), None
        return None, None

    target = intent.get('target') or {}
    item = _resolve_target_item(target, items_snapshot)
    if item is None:
        if len(items_snapshot) == 1:
            item = items_snapshot[0]
        else:
            return None, 'multi_item_number'

    alternatives = item.get('category_alternatives') or []
    index = int(alt_num) - 1
    if index < 0 or index >= len(alternatives):
        return None, 'invalid_alternative'

    return str(alternatives[index]), None


def _resolve_target_item(
    target: Dict[str, Any],
    items_snapshot: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    mode = target.get('mode', 'single')
    if mode in ('all_active', 'unspecified'):
        return None

    line_index = target.get('line_item_index')
    if line_index is not None:
        for item in items_snapshot:
            if item.get('line_item_index') == line_index:
                return item

    hint = (target.get('description_hint') or '').strip().lower()
    if hint:
        for item in items_snapshot:
            desc = str(item.get('description', '')).lower()
            if hint in desc or desc in hint:
                return item

    if len(items_snapshot) == 1:
        return items_snapshot[0]
    return None


def _active_items(items_snapshot: List[Dict[str, Any]], expenses: Dict[str, ExpenseRow]) -> List[Dict[str, Any]]:
    active = []
    for item in items_snapshot:
        expense = expenses.get(str(item.get('expense_id', '')))
        if expense is None or expense.deleted_at:
            continue
        active.append(item)
    return active


def _deleted_items(items_snapshot: List[Dict[str, Any]], expenses: Dict[str, ExpenseRow]) -> List[Dict[str, Any]]:
    deleted = []
    for item in items_snapshot:
        expense = expenses.get(str(item.get('expense_id', '')))
        if expense is not None and expense.deleted_at:
            deleted.append(item)
    return deleted


async def parse_edit_intent(
    user_text: str,
    items_snapshot: List[Dict[str, Any]],
    pending_action: Optional[str],
    gemini: GeminiClient,
) -> Dict[str, Any]:
    if pending_action == 'delete_all' and is_affirmative(user_text):
        return {
            'action': 'confirm_pending',
            'target': {'mode': 'all_active'},
            'updates': {},
            'clarification_needed': False,
            'clarification_message': None,
        }

    bare = _bare_number_intent(user_text, items_snapshot)
    if bare is not None:
        return bare

    prompt = (
        'Parse the user reply to an expense confirmation into EditIntent JSON.\n'
        'Supported languages: Japanese, English, Chinese.\n'
        f'pending_action: {pending_action!r}\n'
        f'items_snapshot: {json.dumps(items_snapshot, ensure_ascii=False)}\n'
        f'user_reply: {user_text!r}\n'
        'Return ONLY JSON with action, target, updates, clarification_needed, clarification_message.'
    )

    try:
        response = await gemini.generate_reply(prompt)
        parsed = validate_edit_intent(_parse_json_object(response))
        if parsed:
            return parsed
    except (json.JSONDecodeError, ValidationError, TypeError):
        logger.warning('parse_edit_intent: invalid LLM JSON', exc_info=True)
    except Exception:
        logger.exception('parse_edit_intent failed')

    return {
        'action': 'clarify',
        'target': {'mode': 'unspecified'},
        'updates': {},
        'clarification_needed': True,
        'clarification_message': None,
    }


def _clarify_message(language: str, reason: str) -> str:
    messages = {
        'multi_item_number': {
            'zh': '有多笔支出。请先说明要改哪一笔（例如「咖啡：2」），再选择编号。',
            'en': 'Multiple items on this confirmation. Identify the item first (e.g. "coffee: 2") before picking a number.',
            'ja': '複数の支出があります。番号を選ぶ前に、対象の項目を指定してください（例：「コーヒー：2」）。',
        },
        'invalid_alternative': {
            'zh': '无效的类别编号。请选择 1–3。',
            'en': 'Invalid category number. Please pick 1–3.',
            'ja': '無効なカテゴリ番号です。1〜3 を選んでください。',
        },
        'ambiguous_target': {
            'zh': '请说明要编辑哪一笔支出。',
            'en': 'Please specify which expense to edit.',
            'ja': '編集する支出を指定してください。',
        },
        'invalid_amount': {
            'zh': '金额无效。请输入正数。',
            'en': 'Invalid amount. Please provide a positive number.',
            'ja': '金額が無効です。正の数値を入力してください。',
        },
        'invalid_date': {
            'zh': '日期无效。请使用 YYYY-MM-DD 格式。',
            'en': 'Invalid date. Use YYYY-MM-DD.',
            'ja': '日付が無効です。YYYY-MM-DD 形式で入力してください。',
        },
        'no_active': {
            'zh': '没有可编辑的有效支出。',
            'en': 'No active expenses to edit on this confirmation.',
            'ja': '編集できる有効な支出がありません。',
        },
        'generic': {
            'zh': '无法理解您的回复。请再试一次。',
            'en': "I couldn't understand that reply. Please try again.",
            'ja': '返信内容を理解できませんでした。もう一度お試しください。',
        },
    }
    table = messages.get(reason, messages['generic'])
    return table.get(language, table['ja'])


def _parse_expense_date(raw: Any) -> Optional[date]:
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


async def apply_edit_intent(
    intent: Dict[str, Any],
    confirmation: ConfirmationRecord,
    user_text: str,
    gemini: GeminiClient,
) -> EditApplyResult:
    language = detect_reply_language(user_text)
    items_snapshot = [dict(item) for item in confirmation.items_snapshot]
    expense_ids = [str(item.get('expense_id', '')) for item in items_snapshot if item.get('expense_id')]
    expenses = {row.id: row for row in get_expenses_by_ids(expense_ids)}

    action = intent.get('action', 'clarify')
    if intent.get('clarification_needed') or action == 'clarify':
        msg = intent.get('clarification_message') or _clarify_message(language, 'generic')
        return EditApplyResult(status='clarification', summary=msg, intent_json=intent, items_snapshot=items_snapshot)

    if action == 'soft_delete_all':
        set_pending_action(confirmation.id, 'delete_all')
        summary = format_edit_result(language, EditSummaryInput(status='applied', action='soft_delete_all_pending'))
        return EditApplyResult(status='applied', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    if action == 'confirm_pending' and confirmation.pending_action == 'delete_all':
        active = _active_items(items_snapshot, expenses)
        ids = [str(item['expense_id']) for item in active]
        result = soft_delete_expenses(ids)
        set_pending_action(confirmation.id, None)
        if not result.success:
            summary = format_edit_result(
                language,
                EditSummaryInput(status='error', action='soft_delete_all', error_message=result.error),
            )
            return EditApplyResult(status='error', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
        summary = format_edit_result(
            language,
            EditSummaryInput(status='applied', action='soft_delete_all', affected_count=result.affected or len(ids)),
        )
        return EditApplyResult(status='applied', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    if action == 'restore_all':
        deleted = _deleted_items(items_snapshot, expenses)
        if not deleted:
            summary = format_edit_result(language, EditSummaryInput(status='no_op', action='restore'))
            return EditApplyResult(status='no_op', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
        ids = [str(item['expense_id']) for item in deleted]
        result = restore_expenses(ids)
        if not result.success:
            summary = format_edit_result(
                language,
                EditSummaryInput(status='error', action='restore_all', error_message=result.error),
            )
            return EditApplyResult(status='error', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
        summary = format_edit_result(
            language,
            EditSummaryInput(status='applied', action='restore_all', affected_count=result.affected),
        )
        return EditApplyResult(status='applied', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    target = intent.get('target') or {}
    mode = target.get('mode', 'single')

    if action in ('soft_delete', 'restore', 'update'):
        if mode == 'all_active' and action == 'soft_delete':
            active = _active_items(items_snapshot, expenses)
            if not active:
                summary = format_edit_result(
                    language,
                    EditSummaryInput(
                        status='clarification',
                        action='soft_delete',
                        clarification_message=_clarify_message(language, 'no_active'),
                    ),
                )
                return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
            ids = [str(item['expense_id']) for item in active]
            result = soft_delete_expenses(ids)
            if not result.success:
                summary = format_edit_result(
                    language,
                    EditSummaryInput(status='error', action='soft_delete', error_message=result.error),
                )
                return EditApplyResult(status='error', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
            summary = format_edit_result(
                language,
                EditSummaryInput(status='applied', action='soft_delete', affected_count=result.affected),
            )
            return EditApplyResult(status='applied', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

        item = _resolve_target_item(target, items_snapshot)
        if item is None and action != 'update':
            summary = format_edit_result(
                language,
                EditSummaryInput(
                    status='clarification',
                    action=action,
                    clarification_message=_clarify_message(language, 'ambiguous_target'),
                ),
            )
            return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

        if action == 'soft_delete':
            expense_id = str(item['expense_id'])
            result = soft_delete_expenses([expense_id])
            if not result.success:
                summary = format_edit_result(
                    language,
                    EditSummaryInput(status='error', action='soft_delete', error_message=result.error),
                )
                return EditApplyResult(status='error', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
            if result.affected == 0:
                summary = format_edit_result(language, EditSummaryInput(status='no_op', action='soft_delete'))
                return EditApplyResult(status='no_op', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
            summary = format_edit_result(
                language,
                EditSummaryInput(
                    status='applied',
                    action='soft_delete',
                    item_description=str(item.get('description', '')),
                    affected_count=1,
                ),
            )
            return EditApplyResult(status='applied', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

        if action == 'restore':
            expense_id = str(item['expense_id'])
            result = restore_expenses([expense_id])
            if not result.success:
                summary = format_edit_result(
                    language,
                    EditSummaryInput(status='error', action='restore', error_message=result.error),
                )
                return EditApplyResult(status='error', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
            if result.affected == 0:
                summary = format_edit_result(language, EditSummaryInput(status='no_op', action='restore'))
                return EditApplyResult(status='no_op', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
            summary = format_edit_result(
                language,
                EditSummaryInput(
                    status='applied',
                    action='restore',
                    item_description=str(item.get('description', '')),
                    affected_count=1,
                ),
            )
            return EditApplyResult(status='applied', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

        if action == 'update':
            if item is None:
                if len(items_snapshot) > 1:
                    summary = format_edit_result(
                        language,
                        EditSummaryInput(
                            status='clarification',
                            action='update',
                            clarification_message=_clarify_message(language, 'ambiguous_target'),
                        ),
                    )
                    return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
                item = items_snapshot[0]

            updates = intent.get('updates') or {}
            expense_id = str(item['expense_id'])
            before_rows = get_expenses_by_ids([expense_id])
            before_row = before_rows[0] if before_rows else None

            category_code, cat_err = resolve_category_pick(intent, items_snapshot)
            if cat_err == 'multi_item_number':
                summary = format_edit_result(
                    language,
                    EditSummaryInput(
                        status='clarification',
                        action='update',
                        clarification_message=_clarify_message(language, 'multi_item_number'),
                    ),
                )
                return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
            if cat_err == 'invalid_alternative':
                summary = format_edit_result(
                    language,
                    EditSummaryInput(
                        status='clarification',
                        action='update',
                        clarification_message=_clarify_message(language, 'invalid_alternative'),
                    ),
                )
                return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

            amount_decimal = None
            if updates.get('amount') is not None:
                try:
                    amount_decimal = Decimal(str(updates['amount'])).quantize(Decimal('0.01'))
                    if amount_decimal <= 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    summary = format_edit_result(
                        language,
                        EditSummaryInput(
                            status='clarification',
                            action='update',
                            clarification_message=_clarify_message(language, 'invalid_amount'),
                        ),
                    )
                    return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

            expense_date_val = _parse_expense_date(updates.get('expense_date'))
            if updates.get('expense_date') is not None and expense_date_val is None:
                summary = format_edit_result(
                    language,
                    EditSummaryInput(
                        status='clarification',
                        action='update',
                        clarification_message=_clarify_message(language, 'invalid_date'),
                    ),
                )
                return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

            description = updates.get('description')
            currency = updates.get('currency')
            if currency is not None:
                currency = str(currency).strip().upper()[:3]

            if not any([description, amount_decimal, currency, expense_date_val, category_code]):
                summary = format_edit_result(
                    language,
                    EditSummaryInput(
                        status='clarification',
                        action='update',
                        clarification_message=_clarify_message(language, 'generic'),
                    ),
                )
                return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

            result = update_expense_fields(
                expense_id,
                description=description,
                amount=amount_decimal,
                currency=currency,
                expense_date=expense_date_val,
                category_code=category_code,
            )
            if not result.success:
                summary = format_edit_result(
                    language,
                    EditSummaryInput(status='error', action='update', error_message=result.error),
                )
                return EditApplyResult(status='error', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

            after_rows = get_expenses_by_ids([expense_id])
            after_row = after_rows[0] if after_rows else None
            changes: List[FieldChange] = []
            if before_row and after_row:
                if description is not None and before_row.description != after_row.description:
                    changes.append(FieldChange('description', before_row.description, after_row.description))
                if amount_decimal is not None and before_row.amount != after_row.amount:
                    changes.append(
                        FieldChange(
                            'amount',
                            format_amount(before_row.amount, before_row.currency),
                            format_amount(after_row.amount, after_row.currency),
                        )
                    )
                if currency is not None and before_row.currency != after_row.currency:
                    changes.append(FieldChange('currency', before_row.currency, after_row.currency))
                if expense_date_val is not None and before_row.expense_date != after_row.expense_date:
                    changes.append(
                        FieldChange(
                            'date',
                            before_row.expense_date.isoformat(),
                            after_row.expense_date.isoformat(),
                        )
                    )
                if category_code is not None and before_row.category_node_id != after_row.category_node_id:
                    old_code = str(item.get('category_guess_code', 'unknown'))
                    changes.append(
                        FieldChange('category', category_path_for_code(old_code), category_path_for_code(category_code))
                    )

            for snap in items_snapshot:
                if str(snap.get('expense_id')) == expense_id:
                    if description is not None:
                        snap['description'] = description
                    if amount_decimal is not None:
                        snap['amount'] = float(amount_decimal)
                    if currency is not None:
                        snap['currency'] = currency
                    if category_code is not None:
                        snap['category_guess_code'] = category_code
                    break

            update_items_snapshot(confirmation.id, items_snapshot)
            summary = format_edit_result(
                language,
                EditSummaryInput(
                    status='applied',
                    action='update',
                    item_description=str(item.get('description', '')),
                    changes=tuple(changes),
                ),
            )
            return EditApplyResult(status='applied', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    summary = format_edit_result(
        language,
        EditSummaryInput(
            status='clarification',
            action='clarify',
            clarification_message=_clarify_message(language, 'generic'),
        ),
    )
    return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
