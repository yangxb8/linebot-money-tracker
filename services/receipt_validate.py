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
_MIN_ITEM_AMOUNT_JPY = Decimal('10')
_MAX_ITEM_AMOUNT_JPY = Decimal('500000')
_MAX_LINE_ITEMS = 30

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


def _is_garbage_item(item: Dict[str, Any]) -> bool:
    description = str(item.get('description', '')).strip()
    if not description or len(description) < 2:
        return True
    if _MASKED_TEXT_RE.search(description):
        return True
    if _PAYMENT_SLIP_RE.search(description):
        return True
    if _METADATA_DESC_RE.match(description):
        return True
    if _PAYMENT_SLIP_RE.search(str(item.get('raw_line', ''))):
        return True

    currency = str(item.get('currency', 'JPY')).strip().upper() or 'JPY'
    try:
        amount = Decimal(str(item.get('amount', 0))).quantize(Decimal('0.01'))
    except Exception:
        return True

    if currency == 'JPY':
        if amount < _MIN_ITEM_AMOUNT_JPY:
            return True
        if amount > _MAX_ITEM_AMOUNT_JPY:
            return True

    return False


def _sum_matches_total(items: List[Dict[str, Any]], ocr_text: str) -> bool:
    totals = extract_receipt_totals(ocr_text)
    target = totals.cash_paid or totals.grand_total
    if target is None or target <= 0:
        return True

    item_sum = sum(Decimal(str(item.get('amount', 0))) for item in items)
    diff = abs(item_sum - target)
    if diff <= _SUM_TOLERANCE:
        return True
    if target > 0 and diff / target <= _SUM_RATIO_TOLERANCE:
        return True

    logger.warning(
        'Receipt validate: item sum %s does not match receipt total %s (diff=%s)',
        item_sum,
        target,
        diff,
    )
    return False


def validate_receipt_items(
    items: List[Dict[str, Any]],
    ocr_text: str = '',
) -> Optional[List[Dict[str, Any]]]:
    """Return cleaned items when trustworthy, else None (do not persist)."""
    if not items:
        return None

    if len(items) > _MAX_LINE_ITEMS:
        logger.warning('Receipt validate: too many items (%d)', len(items))
        return None

    cleaned = [dict(item) for item in items if not _is_garbage_item(item)]
    if not cleaned:
        logger.warning('Receipt validate: all %d item(s) rejected as garbage', len(items))
        return None

    if len(cleaned) < len(items):
        logger.info(
            'Receipt validate: dropped %d garbage item(s), kept %d',
            len(items) - len(cleaned),
            len(cleaned),
        )

    if ocr_text and not _sum_matches_total(cleaned, ocr_text):
        return None

    return cleaned
