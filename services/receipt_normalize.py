"""Normalize receipt line items to final per-item cash-out amounts."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from services.receipt_parser import _JAPANESE_CHAR_REGEX, _normalize_amount, _normalize_text

logger = logging.getLogger(__name__)

_SUM_TOLERANCE = Decimal('2')

_GRAND_TOTAL_RE = re.compile(r'合計\s*[¥￥]?\s*(?P<amount>[\d,]+)', re.I)
_SUBTOTAL_RE = re.compile(r'小計\s*[¥￥]?\s*(?P<amount>[\d,]+)', re.I)
_TAX_LINE_RE = re.compile(
    r'(?:外税|内税|消費税|税額)(?:\s*\d+%)?[^0-9¥￥]*[¥￥]\s*(?P<amount>[\d,]+)',
    re.I,
)
_PAYMENT_RE = re.compile(
    r'(?:iD|ID|カード|現金|支払|お買上|payment)[^0-9¥￥]*[¥￥]?\s*(?P<amount>[\d,]+)',
    re.I,
)
_DISCOUNT_RE = re.compile(
    r'(?:値引|割引|クーポン|ポイント利用|ポイント支払|ポイント使用)[^0-9¥￥\-]*-?\s*[¥￥]?\s*(?P<amount>[\d,]+)',
    re.I,
)
_POINTS_EARNED_RE = re.compile(r'ポイント付与|ポイント獲得|付与ポイント|獲得ポイント', re.I)
_RECEIPT_MARKER_RE = re.compile(r'合計|小計|外税|内税|消費税|領収|レシート|※', re.I)
_METADATA_LINE_RE = re.compile(
    r'(TEL|FAX|登録番号|レジ|責[:：]|会員|伝票|COPY|複製|お客様控え)',
    re.I,
)
_DATETIME_LINE_RE = re.compile(r'\d{4}[/\-年]\s*\d{1,2}[/\-月]\s*\d{1,2}')


@dataclass(frozen=True)
class ReceiptTotals:
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    grand_total: Optional[Decimal] = None
    cash_paid: Optional[Decimal] = None
    discounts: Decimal = Decimal('0')


def looks_like_receipt_text(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    normalized = _normalize_text(text)
    if _RECEIPT_MARKER_RE.search(normalized):
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return len(lines) >= 3 and bool(_JAPANESE_CHAR_REGEX.search(normalized))


def _amount_from_match(pattern: re.Pattern, line: str) -> Optional[Decimal]:
    match = pattern.search(_normalize_text(line))
    if not match:
        return None
    try:
        return _normalize_amount(match.group('amount'))
    except Exception:
        return None


def extract_receipt_totals(ocr_text: str) -> ReceiptTotals:
    subtotal: Optional[Decimal] = None
    tax_total = Decimal('0')
    tax_seen = False
    grand_total: Optional[Decimal] = None
    cash_paid: Optional[Decimal] = None
    discounts = Decimal('0')

    for raw_line in ocr_text.splitlines():
        line = raw_line.strip()
        if not line or _POINTS_EARNED_RE.search(line):
            continue

        if subtotal is None:
            value = _amount_from_match(_SUBTOTAL_RE, line)
            if value is not None:
                subtotal = value

        if '対象額' in line:
            continue

        tax_value = _amount_from_match(_TAX_LINE_RE, line)
        if tax_value is not None:
            tax_total += tax_value
            tax_seen = True

        total_value = _amount_from_match(_GRAND_TOTAL_RE, line)
        if total_value is not None:
            grand_total = total_value

        payment_value = _amount_from_match(_PAYMENT_RE, line)
        if payment_value is not None and '釣' not in line and 'お釣' not in line:
            cash_paid = payment_value

        discount_value = _amount_from_match(_DISCOUNT_RE, line)
        if discount_value is not None:
            discounts += discount_value

    return ReceiptTotals(
        subtotal=subtotal,
        tax=tax_total if tax_seen else None,
        grand_total=grand_total,
        cash_paid=cash_paid,
        discounts=discounts,
    )


def extract_merchant_name(ocr_text: str) -> str:
    for raw_line in ocr_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _METADATA_LINE_RE.search(line) or _DATETIME_LINE_RE.search(line):
            continue
        if _GRAND_TOTAL_RE.search(line) or _SUBTOTAL_RE.search(line):
            continue
        if _JAPANESE_CHAR_REGEX.search(line) and len(line) >= 2:
            return line[:80]
    return 'Expense'


def _item_amounts(items: List[Dict[str, Any]]) -> List[Decimal]:
    return [Decimal(str(item.get('amount', 0))).quantize(Decimal('0.01')) for item in items]


def _apply_amounts(items: List[Dict[str, Any]], amounts: List[Decimal]) -> None:
    for item, amount in zip(items, amounts):
        item['amount'] = float(amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _distribute_proportionally(
    items: List[Dict[str, Any]],
    *,
    target_total: Decimal,
    base_amounts: Optional[List[Decimal]] = None,
) -> None:
    if not items:
        return

    bases = base_amounts or _item_amounts(items)
    base_sum = sum(bases)
    if base_sum <= 0:
        return

    allocated: List[Decimal] = []
    running = Decimal('0')
    for index, base in enumerate(bases):
        if index == len(bases) - 1:
            share = (target_total - running).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            share = (target_total * base / base_sum).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            running += share
        allocated.append(max(share, Decimal('0')))

    _apply_amounts(items, allocated)


def _is_tax_inclusive_receipt(ocr_text: str, totals: ReceiptTotals) -> bool:
    if '内税' in ocr_text:
        return True
    if totals.subtotal and totals.grand_total:
        return abs(totals.subtotal - totals.grand_total) <= _SUM_TOLERANCE
    return False


def _allocate_tax(items: List[Dict[str, Any]], totals: ReceiptTotals) -> None:
    if not items or totals.tax is None or totals.tax <= 0:
        return

    bases = _item_amounts(items)
    base_sum = totals.subtotal if totals.subtotal and totals.subtotal > 0 else sum(bases)
    if base_sum <= 0:
        return

    tax_inclusive = [base + totals.tax * base / base_sum for base in bases]
    _apply_amounts(items, [amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) for amount in tax_inclusive])


def _target_cash_total(totals: ReceiptTotals) -> Optional[Decimal]:
    if totals.cash_paid is not None and totals.cash_paid > 0:
        return totals.cash_paid
    if totals.grand_total is not None and totals.grand_total > 0:
        return totals.grand_total
    return None


def normalize_receipt_items(items: List[Dict[str, Any]], ocr_text: str) -> List[Dict[str, Any]]:
    """Adjust per-line amounts to tax-inclusive cash-out shares."""
    if not items or not looks_like_receipt_text(ocr_text):
        return items

    totals = extract_receipt_totals(ocr_text)
    working = [dict(item) for item in items]

    for item in working:
        if not str(item.get('currency', '')).strip():
            item['currency'] = 'JPY'

    tax_inclusive = _is_tax_inclusive_receipt(ocr_text, totals)
    if not tax_inclusive:
        _allocate_tax(working, totals)

    target = _target_cash_total(totals)
    if target is not None and not tax_inclusive:
        current_sum = sum(_item_amounts(working))
        base_subtotal = totals.subtotal if totals.subtotal and totals.subtotal > 0 else current_sum
        # Do not scale a partial item list up to the receipt total.
        if current_sum >= base_subtotal * Decimal('0.85'):
            if current_sum > target + _SUM_TOLERANCE:
                _distribute_proportionally(working, target_total=target)
            elif current_sum > 0 and abs(current_sum - target) > _SUM_TOLERANCE:
                _distribute_proportionally(working, target_total=target)

    final_sum = sum(_item_amounts(working))
    if target is not None and abs(final_sum - target) > _SUM_TOLERANCE:
        logger.warning(
            'Receipt normalize: item sum %s differs from cash target %s by more than %s',
            final_sum,
            target,
            _SUM_TOLERANCE,
        )
    else:
        logger.info(
            'Receipt normalize: %d item(s) sum=%s target=%s',
            len(working),
            final_sum,
            target,
        )

    return working


def try_total_only_fallback(ocr_text: str) -> List[Dict[str, Any]]:
    """Log a single expense when only the receipt total is readable."""
    if not looks_like_receipt_text(ocr_text):
        return []

    totals = extract_receipt_totals(ocr_text)
    target = _target_cash_total(totals)
    if target is None or target <= 0:
        return []

    merchant = extract_merchant_name(ocr_text)
    logger.info('Receipt normalize: total-only fallback merchant=%r amount=%s', merchant, target)
    return [
        {
            'description': merchant,
            'amount': float(target.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'currency': 'JPY',
            'raw_line': f'{merchant} 合計',
            'confidence': 0.6,
        }
    ]


def finalize_receipt_extraction(items: List[Dict[str, Any]], ocr_text: str) -> List[Dict[str, Any]]:
    """Apply normalization or total-only fallback after OCR/assist extraction."""
    if items:
        return normalize_receipt_items(items, ocr_text)
    return try_total_only_fallback(ocr_text)
