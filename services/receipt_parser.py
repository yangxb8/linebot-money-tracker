import logging
import re
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional, Tuple

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
_YEN_PREFIX_REGEX = re.compile(r'[¥￥]\s*(?P<amount>[\d,]+)\s*(?:外|軽)?')
_TRAILING_AMOUNT_REGEX = re.compile(
    r'(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*(?:円|[A-Za-z]{3}|外|軽)?\s*$',
)
_LEADING_AMOUNT_PREFIX_RE = re.compile(r'^(?P<amount>\d[\d,]*)\s*')
_QUESTION_MARK_RE = re.compile(r'[?？]\s*$')
_SINGLE_LINE_SHORTHAND_MAX_LEN = 40
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


def clean_receipt_description(text: str) -> str:
    """Normalize whitespace and strip trailing punctuation from expense descriptions."""
    cleaned = _normalize_text(text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -@:，、.')
    return cleaned or 'Expense'


def _build_item(line: str, amount: Decimal, currency: str, pattern: re.Pattern) -> Dict[str, Any]:
    desc = pattern.sub('', line).strip(' -@:，、')
    desc = clean_receipt_description(desc)

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


def _match_leading_amount_cjk(line: str) -> Optional[Tuple[Decimal, str, re.Pattern]]:
    """Match terse expense shorthand like '861便利店' or '1200 ランチ' (amount + place)."""
    normalized = _normalize_text(line).strip()
    if not normalized or _QUESTION_MARK_RE.search(normalized):
        return None
    if len(normalized) > _SINGLE_LINE_SHORTHAND_MAX_LEN:
        return None

    match = _LEADING_AMOUNT_PREFIX_RE.match(normalized)
    if not match:
        return None

    remainder = normalized[match.end() :].strip()
    if not remainder or not _looks_japanese(remainder):
        return None

    try:
        amount = _normalize_amount(match.group('amount'))
    except Exception:
        return None

    if amount < Decimal('1') or amount > Decimal('999999'):
        return None

    return amount, 'JPY', _LEADING_AMOUNT_PREFIX_RE


def _parse_single_line_shorthand(text: str) -> List[Dict[str, Any]]:
    """Parse one-line terse expense logs that omit currency markers."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        return []

    matched = _match_leading_amount_cjk(lines[0])
    if not matched:
        return []

    amount, currency, pattern = matched
    return [_build_item(lines[0], amount, currency, pattern)]


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

    trailing = _TRAILING_AMOUNT_REGEX.search(normalized)
    if trailing:
        try:
            amount = _normalize_amount(trailing.group('amount'))
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
    matched = _match_amount(line)
    if not matched:
        return []

    amount, currency, pattern = matched
    return [_build_item(_normalize_text(line), amount, currency, pattern)]


def parse_text_for_expenses(text: str) -> List[Dict[str, Any]]:
    """Parse a single-line chat expense shorthand before LLM assist.

    Supports Western formats (e.g. 'Lunch 120 THB') and Japanese shorthand
    (e.g. 'コーヒー 450円', '861便利店', 'tokyo game show门票 6440').
    Multi-line input returns [] so the LLM path can handle it.
    """
    if not text or not isinstance(text, str):
        logger.info('Text expense parser: skipped (empty or invalid input)')
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        logger.info('Text expense parser: multi-line input skipped (text_len=%d)', len(text))
        return []

    items = _parse_single_line_shorthand(text)
    if not items:
        items = _parse_line(lines[0])

    if items:
        logger.info(
            'Text expense parser: matched %d item(s): %s',
            len(items),
            ', '.join(f'{it["description"]}={it["amount"]} {it["currency"]}' for it in items[:5]),
        )
    else:
        logger.info('Text expense parser: no expense items matched (text_len=%d)', len(text))

    return items
