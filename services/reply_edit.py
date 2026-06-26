from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft7Validator, ValidationError

from services.categorize import map_category_from_text
from services.category_memory import record_user_correction_from_description
from services.confirmation_repository import (
    ConfirmationRecord,
    clear_pending_state,
    set_pending_action,
    set_pending_state,
    update_items_snapshot,
)
from services.expense_repository import (
    ExpenseRow,
    get_expenses_by_ids,
    restore_expenses,
    soft_delete_expenses,
    update_expense_fields,
)
from services.gemini_client import GeminiClient
from services.receipt_parser import _match_amount, _normalize_text
from services.usage_metering import llm_operation_scope
from services.reply_summary import (
    EditSummaryInput,
    FieldChange,
    category_path_for_code,
    describe_category_bulk_intent,
    detect_reply_language,
    format_amount,
    format_category_options_prompt,
    format_edit_result,
    format_intent_confirmation_prompt,
)

logger = logging.getLogger(__name__)


async def _record_category_memory_correction(
    confirmation: ConfirmationRecord,
    *,
    description: str,
    category_code: str,
    gemini: GeminiClient,
    store_name: Optional[str] = None,
) -> None:
    await record_user_correction_from_description(
        confirmation.tenant,
        description=description,
        category_code=category_code,
        gemini=gemini,
        store_name=store_name,
        corrected_by=confirmation.tenant.logged_by_line_user_id,
    )


def _store_name_from_expense_row(expense_row: Optional[ExpenseRow]) -> Optional[str]:
    if expense_row is None or not expense_row.metadata:
        return None
    store = expense_row.metadata.get('store_name')
    if store is not None and str(store).strip():
        return str(store).strip()
    return None

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
                'category_bulk',
                'clarify',
            ],
        },
        'target': {
            'type': 'object',
            'properties': {
                'mode': {
                    'type': 'string',
                    'enum': ['single', 'all_active', 'all_deleted', 'subset', 'unspecified'],
                },
                'line_item_index': {'type': 'integer', 'minimum': 0},
                'line_item_indices': {
                    'type': 'array',
                    'items': {'type': 'integer', 'minimum': 0},
                },
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
                'category_query': {'type': 'string', 'minLength': 1},
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
_CANCEL_PENDING_RE = re.compile(
    r'^(?:no|n|cancel|nevermind|stop|いいえ|キャンセル|取消|不要|算了|不用)$',
    re.IGNORECASE,
)
_DELETE_ALL_PHRASE_RE = re.compile(
    r'^(?:'
    r'delete\s+all|remove\s+all|'
    r'全部(?:取消|删除|削除|删掉)|取消全部|删除全部|削除全部|'
    r'すべて削除|全部削除'
    r')\s*[.!。！]*$',
    re.IGNORECASE,
)
_DELETE_PHRASE_RE = re.compile(
    r'^(?:'
    r'cancel(?:\s+this)?|delete(?:\s+this)?|remove(?:\s+this)?|wrong(?:\s+receipt)?|'
    r'キャンセル|削除(?:して)?|取り消し|取消|間違い|'
    r'删除(?:这个)?|删掉|移除'
    r')\s*[.!。！]*$',
    re.IGNORECASE,
)

REPLY_EDIT_INTENT_PROMPT = """You interpret a user's reply to an expense confirmation on LINE.
The user wants to edit, delete, or restore expense(s) linked to that confirmation.

Return ONLY a JSON object with:
- action: update | soft_delete | soft_delete_all | restore | restore_all | confirm_pending | category_bulk | clarify
- target: {{ "mode": "single"|"all_active"|"all_deleted"|"subset"|"unspecified", "line_item_index"?: int, "line_item_indices"?: int[], "description_hint"?: string }}
- updates: {{ "amount"?: number, "currency"?: string, "description"?: string, "expense_date"?: "YYYY-MM-DD", "category_code"?: string, "category_alternative_number"?: 1|2|3, "category_query"?: string }}
- clarification_needed: boolean
- clarification_message: string or null

Rules:
- Japanese, English, and Chinese are supported.
- If items_snapshot has exactly ONE item, default target to that item (mode=single, line_item_index from snapshot).
- Multi-item confirmations show numbered items 1..N. Prefix edits with item number: "2 3800円", "2 取消", "2 1" (item 2, category alt 1).
- Amount corrections: "打错了，1700", "actually 3800", "应该是1700円", "3800円に修正" → action=update with updates.amount (number, not string).
- "2 3800" / "第2 3800円" on multi-item → update that item's amount.
- "打错了"/"打错了，NNN" means wrong amount typed — UPDATE amount, NOT delete.
- Bare 1/2/3 on single item → category_alternative_number update (pick from existing alternatives).
- Free-text category change: action=category_bulk with updates.category_query (e.g. "餐饮", "交通", "food"). For all items use mode=all_active; for specific items use mode=subset with line_item_indices (0-based).
- "cancel"/"delete"/"キャンセル"/"删除"/"取消" alone → soft_delete (single item) or soft_delete_all (multi-item).
- "delete all"/"全部取消"/"全部删除"/"取消全部" → soft_delete_all (user must reply YES on the confirmation prompt).
- "restore all" → restore_all; "restore"/"undo" → restore.
- When pending_action is delete_all, "取消"/"cancel"/"いいえ" → cancel_pending (not another delete).
- When pending_action is confirm_intent, affirmative → confirm_pending; cancel → cancel_pending.
- When pending_action is category_bulk, bare 1/2/3 → confirm_pending with category_alternative_number in updates.
- Use clarify only when multi-item and the target item cannot be identified.

Examples:
{{"action":"update","target":{{"mode":"single","line_item_index":0}},"updates":{{"amount":1700}},"clarification_needed":false,"clarification_message":null}}
{{"action":"update","target":{{"mode":"single","line_item_index":0}},"updates":{{"amount":3800,"currency":"JPY"}},"clarification_needed":false,"clarification_message":null}}
{{"action":"soft_delete","target":{{"mode":"single","line_item_index":0}},"updates":{{}},"clarification_needed":false,"clarification_message":null}}

pending_action: {pending_action}
items_snapshot: {items_snapshot}
user_reply: {user_reply}
"""


@dataclass
class EditApplyResult:
    status: str
    summary: str
    intent_json: Dict[str, Any]
    items_snapshot: List[Dict[str, Any]] = field(default_factory=list)
    anchor_reply_to_sent_message: bool = False


def is_affirmative(text: str) -> bool:
    return bool(_AFFIRMATIVE_RE.match((text or '').strip()))


def is_cancel_pending(text: str) -> bool:
    return bool(_CANCEL_PENDING_RE.match((text or '').strip()))


def _delete_all_phrase_intent(user_text: str) -> Optional[Dict[str, Any]]:
    if not _DELETE_ALL_PHRASE_RE.match((user_text or '').strip()):
        return None
    return {
        'action': 'soft_delete_all',
        'target': {'mode': 'all_active'},
        'updates': {},
        'clarification_needed': False,
        'clarification_message': None,
        'skip_intent_confirm': True,
    }


def _delete_phrase_intent(
    user_text: str,
    items_snapshot: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    delete_all = _delete_all_phrase_intent(user_text)
    if delete_all is not None:
        return delete_all

    if not _DELETE_PHRASE_RE.match((user_text or '').strip()):
        return None

    if len(items_snapshot) == 1:
        return {
            'action': 'soft_delete',
            'target': {'mode': 'single', 'line_item_index': items_snapshot[0].get('line_item_index', 0)},
            'updates': {},
            'clarification_needed': False,
            'clarification_message': None,
        }

    return {
        'action': 'soft_delete_all',
        'target': {'mode': 'all_active'},
        'updates': {},
        'clarification_needed': False,
        'clarification_message': None,
        'skip_intent_confirm': True,
    }


def _parse_json_object(response: str) -> Any:
    text = response.strip()
    fence_match = _JSON_FENCE_RE.match(text)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _normalize_edit_intent(
    raw: Dict[str, Any],
    items_snapshot: List[Dict[str, Any]],
) -> Dict[str, Any]:
    intent = dict(raw)
    updates = dict(intent.get('updates') or {})

    if updates.get('amount') is not None:
        try:
            amount_text = str(updates['amount']).replace(',', '').strip()
            updates['amount'] = float(amount_text)
        except (TypeError, ValueError):
            updates.pop('amount', None)

    if updates.get('category_alternative_number') is not None:
        try:
            updates['category_alternative_number'] = int(updates['category_alternative_number'])
        except (TypeError, ValueError):
            updates.pop('category_alternative_number', None)

    if updates.get('currency') is not None:
        updates['currency'] = str(updates['currency']).strip().upper()[:3]

    intent['updates'] = updates

    target = dict(intent.get('target') or {})
    action = intent.get('action')
    if len(items_snapshot) == 1 and action in ('update', 'soft_delete', 'restore'):
        if target.get('mode') in (None, 'unspecified', 'single'):
            target['mode'] = 'single'
            if target.get('line_item_index') is None:
                target['line_item_index'] = items_snapshot[0].get('line_item_index', 0)
    intent['target'] = target

    if 'clarification_needed' not in intent:
        intent['clarification_needed'] = action == 'clarify'

    return intent


def validate_edit_intent(
    raw: Any,
    items_snapshot: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    intent = _normalize_edit_intent(raw, items_snapshot or []) if items_snapshot else raw
    try:
        _intent_validator.validate(intent)
    except ValidationError:
        return None
    return intent


def _amount_correction_intent(
    user_text: str,
    items_snapshot: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if len(items_snapshot) != 1:
        return None

    matched = _match_amount(_normalize_text(user_text))
    if matched is None:
        return None

    amount, currency, _ = matched
    if amount <= 0:
        return None

    updates: Dict[str, Any] = {'amount': float(amount)}
    if currency:
        updates['currency'] = currency.upper()

    return {
        'action': 'update',
        'target': {'mode': 'single', 'line_item_index': items_snapshot[0].get('line_item_index', 0)},
        'updates': updates,
        'clarification_needed': False,
        'clarification_message': None,
    }


def _item_prefixed_intent(
    user_text: str,
    items_snapshot: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if len(items_snapshot) <= 1:
        return None

    stripped = user_text.strip()
    match = re.match(r'^(?:第|#)?(\d+)\s*[.:：、,]\s*(.+)$', stripped)
    if not match:
        match = re.match(r'^(?:第|#)?(\d+)\s+(.+)$', stripped)
    if not match:
        return None

    item_num = int(match.group(1))
    rest = match.group(2).strip()
    if item_num < 1 or item_num > len(items_snapshot):
        return None

    line_index = items_snapshot[item_num - 1].get('line_item_index', item_num - 1)
    target = {'mode': 'single', 'line_item_index': line_index}

    if rest in ('1', '2', '3'):
        return {
            'action': 'update',
            'target': target,
            'updates': {'category_alternative_number': int(rest)},
            'clarification_needed': False,
            'clarification_message': None,
        }

    if _DELETE_PHRASE_RE.match(rest):
        return {
            'action': 'soft_delete',
            'target': target,
            'updates': {},
            'clarification_needed': False,
            'clarification_message': None,
        }

    matched = _match_amount(_normalize_text(rest))
    if matched is not None:
        amount, currency, _ = matched
        if amount > 0:
            updates: Dict[str, Any] = {'amount': float(amount)}
            if currency:
                updates['currency'] = currency.upper()
            return {
                'action': 'update',
                'target': target,
                'updates': updates,
                'clarification_needed': False,
                'clarification_message': None,
            }

    return None


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


_CATEGORY_PICK_RE = re.compile(r'^[123]$')


def _parse_item_number_tokens(raw: str) -> List[int]:
    numbers: List[int] = []
    for token in re.split(r'[,\s]+', (raw or '').strip()):
        token = token.strip()
        if not token:
            continue
        if not token.isdigit():
            return []
        numbers.append(int(token))
    return numbers


def _line_indices_for_item_numbers(
    item_numbers: List[int],
    items_snapshot: List[Dict[str, Any]],
) -> Optional[List[int]]:
    if not item_numbers:
        return None
    indices: List[int] = []
    for item_num in item_numbers:
        if item_num < 1 or item_num > len(items_snapshot):
            return None
        indices.append(items_snapshot[item_num - 1].get('line_item_index', item_num - 1))
    return indices


def _looks_like_category_query(rest: str) -> bool:
    stripped = (rest or '').strip()
    if not stripped:
        return False
    if stripped in ('1', '2', '3'):
        return False
    if _DELETE_PHRASE_RE.match(stripped):
        return False
    if _match_amount(_normalize_text(stripped)) is not None:
        return False
    return True


def _category_bulk_intent(
    user_text: str,
    items_snapshot: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    stripped = user_text.strip()
    if not stripped or not _looks_like_category_query(stripped):
        return None

    match = re.match(r'^(?:第|#)?([\d][\d,\s]*)\s+(.+)$', stripped)
    if match:
        item_numbers = _parse_item_number_tokens(match.group(1))
        rest = match.group(2).strip()
        if not item_numbers or not _looks_like_category_query(rest):
            return None
        line_indices = _line_indices_for_item_numbers(item_numbers, items_snapshot)
        if line_indices is None:
            return None
        if len(line_indices) == 1:
            return {
                'action': 'category_bulk',
                'target': {'mode': 'single', 'line_item_index': line_indices[0]},
                'updates': {'category_query': rest},
                'clarification_needed': False,
                'clarification_message': None,
                'skip_intent_confirm': True,
            }
        return {
            'action': 'category_bulk',
            'target': {'mode': 'subset', 'line_item_indices': line_indices},
            'updates': {'category_query': rest},
            'clarification_needed': False,
            'clarification_message': None,
            'skip_intent_confirm': True,
        }

    if len(items_snapshot) == 1:
        return {
            'action': 'category_bulk',
            'target': {
                'mode': 'single',
                'line_item_index': items_snapshot[0].get('line_item_index', 0),
            },
            'updates': {'category_query': stripped},
            'clarification_needed': False,
            'clarification_message': None,
            'skip_intent_confirm': True,
        }

    return None


def _target_line_indices_from_intent(
    intent: Dict[str, Any],
    items_snapshot: List[Dict[str, Any]],
) -> List[int]:
    target = intent.get('target') or {}
    mode = target.get('mode', 'single')
    if mode == 'all_active':
        return [item.get('line_item_index', index) for index, item in enumerate(items_snapshot)]
    if mode == 'subset':
        indices = target.get('line_item_indices') or []
        return [int(index) for index in indices]
    if mode == 'single':
        line_index = target.get('line_item_index')
        if line_index is not None:
            return [int(line_index)]
    if len(items_snapshot) == 1:
        return [items_snapshot[0].get('line_item_index', 0)]
    return []


def _item_labels_for_line_indices(
    line_indices: List[int],
    items_snapshot: List[Dict[str, Any]],
) -> List[str]:
    labels: List[str] = []
    for line_index in line_indices:
        for position, item in enumerate(items_snapshot, start=1):
            if item.get('line_item_index') == line_index:
                labels.append(str(position))
                break
    return labels


def _items_for_line_indices(
    line_indices: List[int],
    items_snapshot: List[Dict[str, Any]],
    expenses: Dict[str, ExpenseRow],
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    wanted = set(line_indices)
    for item in items_snapshot:
        line_index = item.get('line_item_index')
        if line_index not in wanted:
            continue
        expense = expenses.get(str(item.get('expense_id', '')))
        if expense is None or expense.deleted_at:
            continue
        selected.append(item)
    return selected


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
    pending_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if pending_action == 'delete_all' and is_affirmative(user_text):
        return {
            'action': 'confirm_pending',
            'target': {'mode': 'all_active'},
            'updates': {},
            'clarification_needed': False,
            'clarification_message': None,
        }

    if pending_action in ('delete_all', 'confirm_intent', 'category_bulk') and is_cancel_pending(user_text):
        return {
            'action': 'cancel_pending',
            'target': {'mode': 'unspecified'},
            'updates': {},
            'clarification_needed': False,
            'clarification_message': None,
        }

    if pending_action == 'confirm_intent' and is_affirmative(user_text):
        return {
            'action': 'confirm_pending',
            'target': {'mode': 'unspecified'},
            'updates': {},
            'clarification_needed': False,
            'clarification_message': None,
        }

    if pending_action == 'category_bulk' and _CATEGORY_PICK_RE.match((user_text or '').strip()):
        return {
            'action': 'confirm_pending',
            'target': {'mode': 'unspecified'},
            'updates': {'category_alternative_number': int(user_text.strip())},
            'clarification_needed': False,
            'clarification_message': None,
        }

    bare = _item_prefixed_intent(user_text, items_snapshot)
    if bare is not None:
        return bare

    bare = _bare_number_intent(user_text, items_snapshot)
    if bare is not None:
        return bare

    if pending_action is None:
        category_intent = _category_bulk_intent(user_text, items_snapshot)
        if category_intent is not None:
            return category_intent

    if pending_action not in ('delete_all', 'confirm_intent', 'category_bulk'):
        delete_intent = _delete_phrase_intent(user_text, items_snapshot)
        if delete_intent is not None:
            return delete_intent

    prompt = REPLY_EDIT_INTENT_PROMPT.format(
        pending_action=repr(pending_action),
        items_snapshot=json.dumps(items_snapshot, ensure_ascii=False),
        user_reply=repr(user_text),
    )

    try:
        with llm_operation_scope('reply_edit'):
            response = await gemini.generate_json_reply(prompt)
        parsed = validate_edit_intent(_parse_json_object(response), items_snapshot)
        if parsed:
            if parsed.get('action') == 'category_bulk':
                updates = parsed.get('updates') or {}
                if not updates.get('category_query'):
                    parsed['action'] = 'clarify'
                    parsed['clarification_needed'] = True
            return parsed
    except (json.JSONDecodeError, ValidationError, TypeError):
        logger.warning('parse_edit_intent: invalid LLM JSON', exc_info=True)
    except Exception:
        logger.exception('parse_edit_intent failed')

    if pending_action in ('confirm_intent', 'category_bulk'):
        return {
            'action': 'clarify',
            'target': {'mode': 'unspecified'},
            'updates': {},
            'clarification_needed': True,
            'clarification_message': None,
        }

    amount_intent = _amount_correction_intent(user_text, items_snapshot)
    if amount_intent is not None:
        return amount_intent

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
            'zh': '有多笔支出。请用「项目编号 + 修改」回复，例如「2 3800円」或「2 1」选类别。',
            'en': 'Multiple items on this confirmation. Reply with item number + edit, e.g. "2 3800" or "2 1" for category.',
            'ja': '複数の支出があります。「2 3800円」「2 1（カテゴリ）」のように番号付きで返信してください。',
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
        'no_category_match': {
            'zh': '找不到匹配的类别。请换一种说法再试。',
            'en': "Couldn't find a matching category. Please try different wording.",
            'ja': '一致するカテゴリが見つかりませんでした。別の表現でお試しください。',
        },
        'pending_reply': {
            'zh': '请回复 YES 确认，或回复 1–3 选择类别。',
            'en': 'Reply YES to confirm, or 1–3 to pick a category.',
            'ja': 'YES で確認するか、1〜3 でカテゴリを選んでください。',
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


async def _begin_category_bulk_flow(
    intent: Dict[str, Any],
    confirmation: ConfirmationRecord,
    user_text: str,
    gemini: GeminiClient,
    items_snapshot: List[Dict[str, Any]],
    expenses: Dict[str, ExpenseRow],
) -> EditApplyResult:
    language = detect_reply_language(user_text)
    updates = intent.get('updates') or {}
    category_query = str(updates.get('category_query', '')).strip()
    if not category_query:
        summary = format_edit_result(
            language,
            EditSummaryInput(
                status='clarification',
                action='category_bulk',
                clarification_message=_clarify_message(language, 'generic'),
            ),
        )
        return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    line_indices = _target_line_indices_from_intent(intent, items_snapshot)
    target_items = _items_for_line_indices(line_indices, items_snapshot, expenses)
    if not target_items:
        summary = format_edit_result(
            language,
            EditSummaryInput(
                status='clarification',
                action='category_bulk',
                clarification_message=_clarify_message(language, 'no_active'),
            ),
        )
        return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    if not intent.get('skip_intent_confirm'):
        target_labels = tuple(_item_labels_for_line_indices(line_indices, items_snapshot))
        all_items = (intent.get('target') or {}).get('mode') == 'all_active'
        interpretation = describe_category_bulk_intent(language, category_query, target_labels, all_items)
        payload = {
            'interpreted_action': 'category_bulk',
            'category_query': category_query,
            'target_line_item_indices': line_indices,
            'interpretation': interpretation,
        }
        set_pending_state(confirmation.id, 'confirm_intent', payload)
        summary = format_intent_confirmation_prompt(language, interpretation)
        return EditApplyResult(
            status='applied',
            summary=summary,
            intent_json=intent,
            items_snapshot=items_snapshot,
            anchor_reply_to_sent_message=True,
        )

    options = await map_category_from_text(category_query, gemini, tenant=confirmation.tenant)
    if not options:
        summary = format_edit_result(
            language,
            EditSummaryInput(
                status='clarification',
                action='category_bulk',
                clarification_message=_clarify_message(language, 'no_category_match'),
            ),
        )
        return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    target_labels = tuple(_item_labels_for_line_indices(line_indices, items_snapshot))
    payload = {
        'category_query': category_query,
        'category_options': list(options),
        'target_line_item_indices': line_indices,
    }
    set_pending_state(confirmation.id, 'category_bulk', payload)
    summary = format_category_options_prompt(
        language,
        category_query,
        options,
        target_labels,
        tenant=confirmation.tenant,
    )
    return EditApplyResult(
        status='applied',
        summary=summary,
        intent_json=intent,
        items_snapshot=items_snapshot,
        anchor_reply_to_sent_message=True,
    )


async def _apply_category_bulk_pick(
    intent: Dict[str, Any],
    confirmation: ConfirmationRecord,
    user_text: str,
    items_snapshot: List[Dict[str, Any]],
    expenses: Dict[str, ExpenseRow],
    payload: Dict[str, Any],
    gemini: GeminiClient,
) -> EditApplyResult:
    language = detect_reply_language(user_text)
    alt_num = (intent.get('updates') or {}).get('category_alternative_number')
    options = payload.get('category_options') or []
    if alt_num is None or alt_num < 1 or alt_num > len(options):
        summary = format_edit_result(
            language,
            EditSummaryInput(
                status='clarification',
                action='category_bulk',
                clarification_message=_clarify_message(language, 'invalid_alternative'),
            ),
        )
        return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    category_code = str(options[int(alt_num) - 1])
    line_indices = [int(index) for index in (payload.get('target_line_item_indices') or [])]
    target_items = _items_for_line_indices(line_indices, items_snapshot, expenses)
    if not target_items:
        clear_pending_state(confirmation.id)
        summary = format_edit_result(
            language,
            EditSummaryInput(
                status='clarification',
                action='category_bulk',
                clarification_message=_clarify_message(language, 'no_active'),
            ),
        )
        return EditApplyResult(status='clarification', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    updated_count = 0
    for item in target_items:
        expense_id = str(item['expense_id'])
        result = update_expense_fields(
            expense_id,
            category_code=category_code,
            tenant=confirmation.tenant,
        )
        if not result.success:
            summary = format_edit_result(
                language,
                EditSummaryInput(status='error', action='category_bulk', error_message=result.error),
            )
            return EditApplyResult(status='error', summary=summary, intent_json=intent, items_snapshot=items_snapshot)
        updated_count += 1
        expense_row = expenses.get(expense_id)
        description = expense_row.description if expense_row else str(item.get('description', ''))
        await _record_category_memory_correction(
            confirmation,
            description=description,
            category_code=category_code,
            gemini=gemini,
            store_name=_store_name_from_expense_row(expense_row),
        )
        for snap in items_snapshot:
            if str(snap.get('expense_id')) == expense_id:
                snap['category_guess_code'] = category_code
                break

    clear_pending_state(confirmation.id)
    update_items_snapshot(confirmation.id, items_snapshot)
    summary = format_edit_result(
        language,
        EditSummaryInput(
            status='applied',
            action='category_bulk',
            affected_count=updated_count,
            changes=(FieldChange('category', '', category_path_for_code(category_code, confirmation.tenant)),),
        ),
    )
    return EditApplyResult(status='applied', summary=summary, intent_json=intent, items_snapshot=items_snapshot)


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
    pending_payload = dict(confirmation.pending_payload or {})

    if confirmation.pending_action and action not in ('confirm_pending', 'cancel_pending'):
        clear_pending_state(confirmation.id)
        pending_payload = {}

    if intent.get('clarification_needed') or action == 'clarify':
        if confirmation.pending_action in ('confirm_intent', 'category_bulk'):
            msg = intent.get('clarification_message') or _clarify_message(language, 'pending_reply')
        else:
            msg = intent.get('clarification_message') or _clarify_message(language, 'generic')
        return EditApplyResult(status='clarification', summary=msg, intent_json=intent, items_snapshot=items_snapshot)

    if action == 'category_bulk':
        return await _begin_category_bulk_flow(intent, confirmation, user_text, gemini, items_snapshot, expenses)

    if action == 'cancel_pending' and confirmation.pending_action in ('confirm_intent', 'category_bulk'):
        clear_pending_state(confirmation.id)
        if language == 'zh':
            summary = '已取消待确认的操作。'
        elif language == 'en':
            summary = 'Pending action cancelled.'
        else:
            summary = '保留中の操作をキャンセルしました。'
        return EditApplyResult(status='applied', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

    if action == 'confirm_pending' and confirmation.pending_action == 'confirm_intent':
        interpreted_action = pending_payload.get('interpreted_action')
        if interpreted_action == 'category_bulk':
            follow_up = {
                'action': 'category_bulk',
                'target': {
                    'mode': 'subset' if len(pending_payload.get('target_line_item_indices') or []) > 1 else 'single',
                    'line_item_index': (pending_payload.get('target_line_item_indices') or [0])[0],
                    'line_item_indices': pending_payload.get('target_line_item_indices') or [],
                },
                'updates': {'category_query': pending_payload.get('category_query', '')},
                'skip_intent_confirm': True,
            }
            clear_pending_state(confirmation.id)
            return await _begin_category_bulk_flow(
                follow_up,
                confirmation,
                user_text,
                gemini,
                items_snapshot,
                expenses,
            )
        if interpreted_action == 'soft_delete_all':
            clear_pending_state(confirmation.id)
            active = _active_items(items_snapshot, expenses)
            ids = [str(item['expense_id']) for item in active]
            result = soft_delete_expenses(ids)
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

    if action == 'confirm_pending' and confirmation.pending_action == 'category_bulk':
        return await _apply_category_bulk_pick(
            intent, confirmation, user_text, items_snapshot, expenses, pending_payload, gemini
        )

    if action == 'soft_delete_all':
        if not intent.get('skip_intent_confirm'):
            if language == 'zh':
                interpretation = '将软删除此确认中的所有支出。'
            elif language == 'en':
                interpretation = 'Soft-delete all expenses on this confirmation.'
            else:
                interpretation = 'この確認の支出をすべて削除します。'
            payload = {
                'interpreted_action': 'soft_delete_all',
                'interpretation': interpretation,
            }
            set_pending_state(confirmation.id, 'confirm_intent', payload)
            summary = format_intent_confirmation_prompt(language, interpretation)
            return EditApplyResult(
                status='applied',
                summary=summary,
                intent_json=intent,
                items_snapshot=items_snapshot,
                anchor_reply_to_sent_message=True,
            )
        set_pending_action(confirmation.id, 'delete_all')
        summary = format_edit_result(language, EditSummaryInput(status='applied', action='soft_delete_all_pending'))
        return EditApplyResult(
            status='applied',
            summary=summary,
            intent_json=intent,
            items_snapshot=items_snapshot,
            anchor_reply_to_sent_message=True,
        )

    if action == 'cancel_pending' and confirmation.pending_action == 'delete_all':
        set_pending_action(confirmation.id, None)
        if language == 'zh':
            summary = '已取消批量删除。'
        elif language == 'en':
            summary = 'Bulk delete cancelled.'
        else:
            summary = '一括削除をキャンセルしました。'
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
                tenant=confirmation.tenant,
            )
            if not result.success:
                summary = format_edit_result(
                    language,
                    EditSummaryInput(status='error', action='update', error_message=result.error),
                )
                return EditApplyResult(status='error', summary=summary, intent_json=intent, items_snapshot=items_snapshot)

            after_rows = get_expenses_by_ids([expense_id])
            after_row = after_rows[0] if after_rows else None
            if (
                category_code is not None
                and before_row
                and after_row
                and before_row.category_node_id != after_row.category_node_id
            ):
                await _record_category_memory_correction(
                    confirmation,
                    description=before_row.description,
                    category_code=category_code,
                    gemini=gemini,
                    store_name=_store_name_from_expense_row(before_row),
                )
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
                        FieldChange(
                            'category',
                            category_path_for_code(old_code, confirmation.tenant),
                            category_path_for_code(category_code, confirmation.tenant),
                        )
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
