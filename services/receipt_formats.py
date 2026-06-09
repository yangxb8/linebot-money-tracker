"""Format-specific preprocessors and parsers for common Japanese receipt layouts."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from services.receipt_parser import (
    _JAPANESE_CHAR_REGEX,
    _build_item,
    _finalize_receipt_items,
    _is_receipt_metadata_line,
    _is_receipt_summary_line,
    _normalize_amount,
    _normalize_text,
    _parse_line,
    clean_receipt_description,
    preprocess_wrapped_receipt_lines,
    split_compound_receipt_line,
)

logger = logging.getLogger(__name__)

_FORMAT_IKEA = 'ikea'
_FORMAT_DAISO = 'daiso'
_FORMAT_RESTAURANT = 'restaurant'
_FORMAT_GENERIC = 'generic'

_POINTS_SECTION_START_RE = re.compile(r'={3,}\s*ポイント', re.I)
_POINTS_SECTION_END_RE = re.compile(r'={3,}', re.I)
_QTY_DETAIL_RE = re.compile(r'^\(@\s*[\d,]+\s*x\s*\d+', re.I)
_IKEA_PRODUCT_HEADER_RE = re.compile(r'商品名\s*(?P<code>\d{6,8})', re.I)
_IKEA_PRICE_LINE_RE = re.compile(
    r'^(?:(?P<qty>\d+)\s*\*\s*(?P<unit>[\d,]+)\s+)?(?P<total>[\d,]+)\s+0\s*$',
)
_RESTAURANT_ROW_RE = re.compile(
    r'^(?P<name>[\u4e00-\u9fff\u3040-\u30ff]+(?:[\u4e00-\u9fff\u3040-\u30ff\s]*[\u4e00-\u9fff\u3040-\u30ff]+)?)'
    r'\s+(?P<qty>\d+)\s+@?\s*(?P<unit>[\d,]+)\s+(?P<amount>[\d,]+)\s*※?\s*$',
)
_CJK_CHAR_RE = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def detect_receipt_format(ocr_text: str) -> str:
    normalized = _normalize_text(ocr_text)
    if '商品名' in normalized and _IKEA_PRODUCT_HEADER_RE.search(normalized):
        return _FORMAT_IKEA
    if '(@' in normalized and ('外' in normalized or '※' in normalized):
        return _FORMAT_DAISO
    if _RESTAURANT_ROW_RE.search(normalized) or (
        '※' in normalized and '@' in normalized and bool(re.search(r'[\u4e00-\u9fff]{2,}\s+\d+\s+@', normalized))
    ):
        return _FORMAT_RESTAURANT
    return _FORMAT_GENERIC


def _strip_points_section(lines: List[str]) -> List[str]:
    kept: List[str] = []
    in_points = False
    for line in lines:
        if _POINTS_SECTION_START_RE.search(line):
            in_points = True
            continue
        if in_points:
            if _POINTS_SECTION_END_RE.search(line) and not _POINTS_SECTION_START_RE.search(line):
                in_points = False
            continue
        if in_points:
            continue
        kept.append(line)
    return kept


def _attach_qty_detail_lines(lines: List[str]) -> List[str]:
    """Merge Daiso-style (@100 x 6個) lines onto the previous priced line."""
    merged: List[str] = []
    for line in lines:
        if _QTY_DETAIL_RE.match(line.strip()) and merged:
            merged[-1] = f'{merged[-1]} {line.strip()}'
        else:
            merged.append(line)
    return merged


def preprocess_format_lines(lines: List[str], ocr_text: str) -> List[str]:
    fmt = detect_receipt_format(ocr_text)
    lines = _strip_points_section(lines)
    if fmt == _FORMAT_DAISO:
        lines = _attach_qty_detail_lines(lines)
    return lines


def _tax_rate_hint_from_line(line: str) -> Optional[str]:
    normalized = _normalize_text(line)
    if re.search(r'※|軽', normalized):
        return '8'
    if re.search(r'外', normalized):
        return '10'
    return None


def _item_with_tax_hint(line: str, amount: Decimal, currency: str, pattern: re.Pattern) -> Dict[str, Any]:
    item = _build_item(line, amount, currency, pattern)
    hint = _tax_rate_hint_from_line(line)
    if hint:
        item['tax_rate_hint'] = hint
    return item


def parse_ikea_receipt(lines: List[str], full_text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    pending_name: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or _is_receipt_summary_line(line) or _is_receipt_metadata_line(line):
            pending_name = []
            continue

        if _IKEA_PRODUCT_HEADER_RE.search(line):
            pending_name = []
            while i < len(lines):
                peek = lines[i].strip()
                if not peek or _IKEA_PRODUCT_HEADER_RE.search(peek) or _IKEA_PRICE_LINE_RE.match(peek):
                    break
                if _is_receipt_summary_line(peek):
                    break
                pending_name.append(peek)
                i += 1
            continue

        price_match = _IKEA_PRICE_LINE_RE.match(line)
        if price_match and pending_name:
            total = _normalize_amount(price_match.group('total'))
            desc = clean_receipt_description(' '.join(pending_name))
            qty = price_match.group('qty')
            unit = price_match.group('unit')
            if qty and unit:
                desc = f'{desc} ({qty}x{unit})'
            items.append(
                {
                    'description': desc,
                    'amount': float(total),
                    'currency': 'JPY',
                    'raw_line': line,
                    'confidence': 0.85,
                }
            )
            pending_name = []
            continue

        pending_name = []

    return _finalize_receipt_items(items, full_text)


def parse_restaurant_receipt(lines: List[str], full_text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for line in lines:
        if not line or _is_receipt_summary_line(line) or _is_receipt_metadata_line(line):
            continue
        match = _RESTAURANT_ROW_RE.match(_normalize_text(line.strip()))
        if not match:
            continue
        amount = _normalize_amount(match.group('amount'))
        desc = clean_receipt_description(match.group('name').strip())
        qty = match.group('qty')
        items.append(
            {
                'description': f'{desc} x{qty}' if qty != '1' else desc,
                'amount': float(amount),
                'currency': 'JPY',
                'raw_line': line,
                'tax_rate_hint': '8',
                'confidence': 0.85,
            }
        )
    return _finalize_receipt_items(items, full_text)


def parse_generic_receipt_lines(
    lines: List[str],
    full_text: str,
    *,
    skip_wrapped: bool = False,
) -> List[Dict[str, Any]]:
    if not skip_wrapped:
        lines = preprocess_wrapped_receipt_lines(lines)
    items: List[Dict[str, Any]] = []
    for line in lines:
        for segment in split_compound_receipt_line(line):
            normalized = _normalize_text(segment)
            if _is_receipt_metadata_line(normalized):
                continue
            parsed = _parse_line(segment)
            if not parsed:
                continue
            hint = _tax_rate_hint_from_line(segment)
            if hint is None and re.search(r'\d{2}\*', normalized):
                hint = '8'
            if hint:
                parsed[0]['tax_rate_hint'] = hint
            items.extend(parsed)
    return _finalize_receipt_items(items, full_text)


def parse_receipt_by_format(text: str) -> List[Dict[str, Any]]:
    if not text or not isinstance(text, str):
        return []

    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    lines = preprocess_format_lines(raw_lines, text)
    fmt = detect_receipt_format(text)

    if fmt == _FORMAT_IKEA:
        items = parse_ikea_receipt(lines, text)
        if items:
            logger.info('Receipt format: ikea matched %d item(s)', len(items))
            return items

    if fmt == _FORMAT_RESTAURANT:
        items = parse_restaurant_receipt(lines, text)
        if items:
            logger.info('Receipt format: restaurant matched %d item(s)', len(items))
            return items

    items = parse_generic_receipt_lines(lines, text, skip_wrapped=(fmt == _FORMAT_DAISO))
    logger.info('Receipt format: %s matched %d item(s)', fmt, len(items))
    return items
