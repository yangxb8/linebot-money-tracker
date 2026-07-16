"""Validate parsed receipt line items before logging."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional

from services.receipt_normalize import extract_receipt_totals

logger = logging.getLogger(__name__)

_SUM_TOLERANCE = Decimal('2')
_SUM_RATIO_TOLERANCE = Decimal('0.05')
_PARTIAL_PARSE_RATIO = Decimal('0.85')
_MAX_SCALE_RATIO = Decimal('2.5')

_ITEM_COUNT_RE = re.compile(r'(?:買上点数|購入点数)\s*(\d+)', re.I)
_SUBTOTAL_ITEM_COUNT_RE = re.compile(r'小計[^\\n]*?(\d+)\s*点', re.I)
_MIN_ITEM_AMOUNT_JPY = Decimal('1')
_MAX_ITEM_AMOUNT_JPY = Decimal('500000')
_MAX_LINE_ITEMS = 30
_MAX_ITEM_TO_TOTAL_RATIO = Decimal('10')

_MASKED_TEXT_RE = re.compile(r'\*{2,}|X{4,}', re.I)
_PAYMENT_SLIP_RE = re.compile(
    r'(カード会社|クレジット|売上票|伝票番号|承認番号|会員番号|'
    r'お客様控え|i\s*D|iD支払|dカード|card\s*company|approval|'
    r'金額\s*\\|合\s*it|丘票)',
    re.I,
)
_METADATA_DESC_RE = re.compile(
    r'^(i\s*EONS|EONS|COPY|複製|領収証|register|receipt)$',
    re.I,
)
# Single-kanji product names are common on JP receipts (桃, 卵, 茶, …).
_CJK_CHAR_RE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')


def _item_log_label(item: Dict[str, Any]) -> str:
    description = str(item.get('description', '')).strip()
    return f'{description!r}={item.get("amount")}'


def _garbage_reason(item: Dict[str, Any]) -> Optional[str]:
    """Return why an item is untrustworthy, or None if it looks like a product line."""
    description = str(item.get('description', '')).strip()
    if not description:
        return 'empty_description'
    # Allow any non-empty description, including single kanji (桃). Only reject
    # ASCII noise like "." / "A" when there is no CJK content.
    if len(description) < 2 and not _CJK_CHAR_RE.search(description):
        return 'short_ascii_description'
    if _MASKED_TEXT_RE.search(description):
        return 'masked_text'
    if _PAYMENT_SLIP_RE.search(description):
        return 'payment_slip_description'
    if _METADATA_DESC_RE.match(description):
        return 'metadata_description'
    if _PAYMENT_SLIP_RE.search(str(item.get('raw_line', ''))):
        return 'payment_slip_raw_line'

    currency = str(item.get('currency', 'JPY')).strip().upper() or 'JPY'
    try:
        amount = Decimal(str(item.get('amount', 0))).quantize(Decimal('0.01'))
    except Exception:
        return 'invalid_amount'

    if currency == 'JPY':
        if amount < _MIN_ITEM_AMOUNT_JPY:
            return 'amount_too_small'
        if amount > _MAX_ITEM_AMOUNT_JPY:
            return 'amount_too_large'

    return None


def _is_garbage_item(item: Dict[str, Any]) -> bool:
    return _garbage_reason(item) is not None


def _expected_item_count(ocr_text: str) -> Optional[int]:
    match = _ITEM_COUNT_RE.search(ocr_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    subtotal_match = _SUBTOTAL_ITEM_COUNT_RE.search(ocr_text)
    if subtotal_match:
        try:
            return int(subtotal_match.group(1))
        except ValueError:
            pass
    return None


def _is_complete_parse(items: List[Dict[str, Any]], ocr_text: str) -> bool:
    totals = extract_receipt_totals(ocr_text)
    item_sum = sum(Decimal(str(item.get('amount', 0))) for item in items)

    expected = _expected_item_count(ocr_text)
    if expected is not None and len(items) < expected:
        logger.warning(
            'Receipt validate: parsed %d item(s) but receipt shows %d',
            len(items),
            expected,
        )
        return False

    if totals.subtotal and totals.subtotal > 0:
        if item_sum < totals.subtotal * _PARTIAL_PARSE_RATIO:
            logger.warning(
                'Receipt validate: item sum %s is far below subtotal %s (partial parse)',
                item_sum,
                totals.subtotal,
            )
            return False

    target = totals.cash_paid or totals.grand_total
    if target and item_sum > 0 and item_sum < target / _MAX_SCALE_RATIO:
        logger.warning(
            'Receipt validate: item sum %s too small vs total %s to trust scaling',
            item_sum,
            target,
        )
        return False

    return True


def _item_amounts_sane_for_target(items: List[Dict[str, Any]], target: Decimal) -> bool:
    if target is None or target <= 0:
        return True

    for item in items:
        try:
            amount = Decimal(str(item.get('amount', 0)))
        except Exception:
            return False
        if amount > target * _MAX_ITEM_TO_TOTAL_RATIO:
            logger.warning(
                'Receipt validate: item amount %s exceeds %sx receipt total %s',
                amount,
                _MAX_ITEM_TO_TOTAL_RATIO,
                target,
            )
            return False
        if target < Decimal('5000') and amount > Decimal('10000'):
            logger.warning(
                'Receipt validate: item amount %s too large for small receipt total %s',
                amount,
                target,
            )
            return False
    return True


def _item_amounts_sane(items: List[Dict[str, Any]], ocr_text: str) -> bool:
    totals = extract_receipt_totals(ocr_text)
    target = totals.cash_paid or totals.grand_total
    if target is None or target <= 0:
        return True
    return _item_amounts_sane_for_target(items, target)


def _sum_matches_target(items: List[Dict[str, Any]], target: Decimal) -> bool:
    if target is None or target <= 0:
        return True

    item_sum = sum(Decimal(str(item.get('amount', 0))) for item in items)
    diff = abs(item_sum - target)
    if diff <= _SUM_TOLERANCE:
        return True
    if target > 0 and diff / target <= _SUM_RATIO_TOLERANCE:
        return True

    logger.warning(
        'Receipt validate: item sum %s does not match receipt total %s (diff=%s) items=[%s]',
        item_sum,
        target,
        diff,
        ', '.join(_item_log_label(item) for item in items[:20]),
    )
    return False


def _sum_matches_total(items: List[Dict[str, Any]], ocr_text: str) -> bool:
    totals = extract_receipt_totals(ocr_text)
    target = totals.cash_paid or totals.grand_total
    if target is None or target <= 0:
        return True
    return _sum_matches_target(items, target)


def validate_receipt_items(
    items: List[Dict[str, Any]],
    ocr_text: str = '',
    *,
    receipt_total: Optional[Decimal] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Return cleaned items when trustworthy, else None (do not persist)."""
    if not items:
        return None

    if len(items) > _MAX_LINE_ITEMS:
        logger.warning('Receipt validate: too many items (%d)', len(items))
        return None

    garbage: List[Dict[str, Any]] = []
    cleaned: List[Dict[str, Any]] = []
    for item in items:
        if _is_garbage_item(item):
            garbage.append(item)
        else:
            cleaned.append(dict(item))
    if not cleaned:
        logger.warning(
            'Receipt validate: all %d item(s) rejected as garbage: [%s]',
            len(items),
            ', '.join(_item_log_label(item) for item in items[:20]),
        )
        return None

    if garbage:
        dropped_detail = ', '.join(
            f'{_item_log_label(item)}({_garbage_reason(item)})' for item in garbage[:10]
        )
        logger.info(
            'Receipt validate: dropped %d garbage item(s), kept %d; dropped=[%s]',
            len(garbage),
            len(cleaned),
            dropped_detail,
        )

    if receipt_total is not None:
        if not _sum_matches_target(cleaned, receipt_total):
            return None
        if not _item_amounts_sane_for_target(cleaned, receipt_total):
            return None
        return cleaned

    if ocr_text and not _is_complete_parse(cleaned, ocr_text):
        return None

    if ocr_text and not _sum_matches_total(cleaned, ocr_text):
        return None

    if ocr_text and not _item_amounts_sane(cleaned, ocr_text):
        return None

    return cleaned
