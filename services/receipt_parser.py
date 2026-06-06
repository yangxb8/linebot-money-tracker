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


def _build_item(line: str, amount: Decimal, currency: str, pattern: re.Pattern) -> Dict[str, Any]:
    desc = pattern.sub('', line).strip(' -@:，、')
    if not desc:
        desc = 'Expense'

    return {
        'description': desc,
        'amount': float(amount),
        'currency': currency.upper() if currency else '',
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
        return amount, currency, _AMOUNT_CURRENCY_REGEX

    return None


def _parse_line(line: str) -> List[Dict[str, Any]]:
    normalized = _normalize_text(line)
    matched = _match_amount(normalized)
    if not matched:
        return []

    amount, currency, pattern = matched
    return [_build_item(normalized, amount, currency, pattern)]


def parse_text_for_expenses(text: str) -> List[Dict[str, Any]]:
    """Parse a free-form text input and return a list of expense items.

    Supports Western formats (e.g. 'Lunch 120 THB') and Japanese receipts
    (e.g. 'コーヒー 450円', '合計 ¥1,280', full-width digits).
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

    if items:
        logger.info(
            'Receipt parser: matched %d item(s): %s',
            len(items),
            ', '.join(f'{it["description"]}={it["amount"]} {it["currency"]}' for it in items[:5]),
        )
    else:
        logger.info('Receipt parser: no expense items matched from %d line(s)', len(lines))

    return items
