import logging
import re
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional, Tuple

from services.log_utils import truncate

logger = logging.getLogger(__name__)

# Full-width digits and common Japanese receipt symbols → half-width.
_FULLWIDTH_TRANS = str.maketrans(
    '０１２３４５６７８９，．￥',
    '0123456789,.¥',
)

_AMOUNT_CURRENCY_REGEX = re.compile(
    r"(?P<amount>\d+[\d,\.]*)(?:\s*)(?P<currency>[A-Za-z]{3}|THB|USD|EUR|JPY|SGD|AUD|GBP|\$|€|¥|฿)?",
    re.I,
)
_YEN_SUFFIX_REGEX = re.compile(r'(?P<amount>[\d,]+)\s*円')
_YEN_PREFIX_REGEX = re.compile(r'[¥￥]\s*(?P<amount>[\d,]+)')
_YEN_TAX_MARKER_REGEX = re.compile(r'(?P<amount>[\d,]+)\s*※')
_TRAILING_AMOUNT_REGEX = re.compile(
    r'(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*(?:※|円|[A-Za-z]{3})?\s*$',
)

_RECEIPT_SUMMARY_REGEX = re.compile(
    r'(小計|合計|外税|内税|消費税|税額|対象額|お釣り|釣り|預り|値引|割引|ポイント|'
    r'subtotal|total|tax|change|balance\s+due)',
    re.I,
)
_RECEIPT_METADATA_REGEX = re.compile(
    r'(TEL|FAX|登録番号|レジ|責[:：]|会員|伝票|承認|COPY|複製|領収|お客様控え|'
    r'クレジット|売上票|register|receipt\s+no|支払|お買上|payment)',
    re.I,
)
_DATETIME_LINE_REGEX = re.compile(
    r'\d{4}[/\-年]\s*\d{1,2}[/\-月]\s*\d{1,2}',
)
_JAPANESE_CHAR_REGEX = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def _normalize_text(text: str) -> str:
    return text.translate(_FULLWIDTH_TRANS)


def _normalize_amount(raw: str) -> Decimal:
    s = _normalize_text(raw).replace(',', '').replace(' ', '')
    s = s.replace('\u00A0', '')
    try:
        return Decimal(s)
    except InvalidOperation:
        s2 = s.replace('.', '').replace(',', '.')
        return Decimal(s2)


def _looks_japanese(text: str) -> bool:
    return bool(_JAPANESE_CHAR_REGEX.search(text))


def _is_receipt_summary_line(line: str) -> bool:
    return bool(_RECEIPT_SUMMARY_REGEX.search(line))


def _is_receipt_metadata_line(line: str) -> bool:
    return bool(_RECEIPT_METADATA_REGEX.search(line))


def _build_item(line: str, amount: Decimal, currency: str, pattern: re.Pattern) -> Dict[str, Any]:
    desc = pattern.sub('', line).strip(' -@:，、')
    if not desc:
        desc = 'Expense'

    normalized_currency = currency.upper() if currency else ''
    if not normalized_currency and _looks_japanese(line):
        normalized_currency = 'JPY'

    return {
        'description': desc,
        'amount': float(amount),
        'currency': normalized_currency,
        'raw_line': line,
        'confidence': 0.8,
    }


def _match_amount(line: str) -> Optional[Tuple[Decimal, str, re.Pattern]]:
    normalized = _normalize_text(line)

    yen_suffix = _YEN_SUFFIX_REGEX.search(normalized)
    if yen_suffix:
        try:
            return _normalize_amount(yen_suffix.group('amount')), 'JPY', _YEN_SUFFIX_REGEX
        except Exception:
            pass

    yen_prefix = _YEN_PREFIX_REGEX.search(normalized)
    if yen_prefix:
        try:
            return _normalize_amount(yen_prefix.group('amount')), 'JPY', _YEN_PREFIX_REGEX
        except Exception:
            pass

    yen_marker = _YEN_TAX_MARKER_REGEX.search(normalized)
    if yen_marker:
        try:
            return _normalize_amount(yen_marker.group('amount')), 'JPY', _YEN_TAX_MARKER_REGEX
        except Exception:
            pass

    trailing = _TRAILING_AMOUNT_REGEX.search(normalized)
    if trailing:
        amount_raw = trailing.group('amount')
        try:
            amount = _normalize_amount(amount_raw)
        except Exception:
            return None
        currency = 'JPY' if _looks_japanese(normalized) else ''
        return amount, currency, _TRAILING_AMOUNT_REGEX

    western = _AMOUNT_CURRENCY_REGEX.search(normalized)
    if western:
        amount_raw = western.group('amount')
        currency = western.group('currency') or ''
        try:
            amount = _normalize_amount(amount_raw)
        except Exception:
            return None
        if currency in ('¥', '￥'):
            currency = 'JPY'
        # Bare numbers mid-line (e.g. 瀬ヶ崎3丁目) are not expense amounts.
        if not currency and western.end() != len(normalized):
            return None
        if not currency and _looks_japanese(normalized):
            currency = 'JPY'
        return amount, currency, _AMOUNT_CURRENCY_REGEX

    return None


def _parse_line(line: str) -> List[Dict[str, Any]]:
    normalized = _normalize_text(line)
    if _is_receipt_metadata_line(normalized) or _DATETIME_LINE_REGEX.search(normalized):
        return []

    matched = _match_amount(normalized)
    if not matched:
        return []

    amount, currency, pattern = matched
    return [_build_item(normalized, amount, currency, pattern)]


def _finalize_receipt_items(items: List[Dict[str, Any]], full_text: str) -> List[Dict[str, Any]]:
    if not items:
        return items

    product_like = [
        item
        for item in items
        if not _is_receipt_summary_line(str(item.get('raw_line', '')))
        and not _is_receipt_metadata_line(str(item.get('raw_line', '')))
    ]
    if product_like:
        items = product_like

    if _looks_japanese(full_text):
        for item in items:
            if not str(item.get('currency', '')).strip():
                item['currency'] = 'JPY'

    return items


def parse_text_for_expenses(text: str) -> List[Dict[str, Any]]:
    """Parse a free-form text input and return a list of expense items.

    Supports Western formats (e.g. 'Lunch 120 THB') and Japanese receipts
    (e.g. 'コーヒー 450円', '合計 ¥1,280', '159※', full-width digits).
    """
    if not text or not isinstance(text, str):
        logger.info('Receipt parser: skipped (empty or invalid input)')
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        logger.info('Receipt parser: no non-empty lines in input (text_len=%d)', len(text))
        return []

    logger.info('Receipt parser: scanning %d line(s), text_len=%d', len(lines), len(text))
    logger.debug('Receipt parser input sample: %s', truncate('\n'.join(lines[:10]), 800))

    items: List[Dict[str, Any]] = []
    for line in lines:
        items.extend(_parse_line(line))

    items = _finalize_receipt_items(items, text)

    if items:
        logger.info(
            'Receipt parser: matched %d item(s): %s',
            len(items),
            ', '.join(f'{it["description"]}={it["amount"]} {it["currency"]}' for it in items[:5]),
        )
    else:
        logger.info('Receipt parser: no expense items matched from %d line(s)', len(lines))

    return items
