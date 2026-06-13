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
_YEN_PREFIX_REGEX = re.compile(r'[¥￥]\s*(?P<amount>[\d,]+)\s*(?:外|軽)?')
_YEN_TAX_MARKER_REGEX = re.compile(r'※\s*\\?\s*(?P<amount>[\d,]+)\s*[A-Za-z]?')
_YEN_TAX_MARKER_TRAILING_REGEX = re.compile(
    r'(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*※\s*\\?\s*[A-Za-z]?\s*$',
)
_TRAILING_AMOUNT_REGEX = re.compile(
    r'(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*(?:※\s*\\?\s*[A-Za-z]?|円|[A-Za-z]{3}|外|軽)?\s*$',
)
_JAN_PRODUCT_CODE_RE = re.compile(r'P\d{13}')
_SHELF_PREFIX_RE = re.compile(r'内\d+\s+\d{4}\s*')
_REGISTER_NOISE_RE = re.compile(
    r'999999精算機|精算機|GGL|\*#%|\*%%|["\']999999',
    re.I,
)
_DESC_NOISE_RE = re.compile(
    r'P\d{13}|内\d+\s+\d{4}\s*|\d{2}\*\s*|999999精算機|精算機|GGL|\*#%|\*%%|["\']|\(@\s*[\d,]+\s*x\s*\d+[^)]*\)',
    re.I,
)
_TRAILING_BARE_PRICE_RE = re.compile(r'(?P<amount>[\d,]{3,5})(?:\.\d{1,2})?\s*$')
_LEADING_AMOUNT_PREFIX_RE = re.compile(r'^(?P<amount>\d[\d,]*)\s*')
_QUESTION_MARK_RE = re.compile(r'[?？]\s*$')
_SINGLE_LINE_SHORTHAND_MAX_LEN = 40

_RECEIPT_SUMMARY_REGEX = re.compile(
    r'(小計|合計|外税|内税|消費税|税額|対象|お釣り|釣り|預り|値引|割引|ポイント|買上点数|購入点数|'
    r'\bsubtotal\b|\btotal\b|\btax\b|\bchange\b|balance\s+due)',
    re.I,
)
_TAX_TARGET_LINE_RE = re.compile(r'\d+%?\s*対象', re.I)
_RECEIPT_METADATA_REGEX = re.compile(
    r'(TEL|FAX|登録番号|レジ|責[:：]|会員|伝票|承認|COPY|複製|領収|お客様控え|'
    r'クレジット|売上票|register|receipt\s+no|支払|お買上|payment|電子マネー|コード支払|コード決済)',
    re.I,
)
_PHONE_LINE_RE = re.compile(r'^[\d\-]{10,14}$')
_DATETIME_LINE_REGEX = re.compile(
    r'\d{4}[/\-年]\s*\d{1,2}[/\-月]\s*\d{1,2}',
)
_JAPANESE_CHAR_REGEX = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
_PRICE_AT_END_RE = re.compile(
    r'[¥￥]\s*[\d,]+(?:\.\d{1,2})?\s*(?:外|軽)?\s*$|'
    r'[\d,]+(?:\.\d{1,2})?\s*(?:円|※\s*\\?\s*[A-Za-z]?|外|軽)\s*$|'
    r'※\s*\\?\s*[\d,]+\s*$|'
    r':\s*[\d,]+(?:\.\d{1,2})?\s*$',
)


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


def clean_receipt_description(text: str) -> str:
    """Strip JAN codes, shelf prefixes, and register OCR noise for display/LLM."""
    cleaned = _normalize_text(text)
    cleaned = _DESC_NOISE_RE.sub(' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -@:，、.')
    cleaned = re.sub(r'^(?:\d{4,}\s+)+', '', cleaned).strip(' -@:，、.')
    return cleaned or 'Expense'


def _fix_ocr_price_amount(amount: Decimal, line: str = '') -> Decimal:
    """Recover shelf prices when OCR misreads ¥249 as 4249."""
    normalized = _normalize_text(line)
    if _PHONE_LINE_RE.match(normalized.strip()):
        return amount
    if amount >= 4000 and amount < 10000:
        candidate = amount % 1000
        if Decimal('50') <= candidate <= Decimal('2000'):
            return candidate
    return amount


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

    yen_marker = _YEN_TAX_MARKER_REGEX.search(normalized)
    if yen_marker:
        try:
            amount = _fix_ocr_price_amount(_normalize_amount(yen_marker.group('amount')), normalized)
            return amount, 'JPY', _YEN_TAX_MARKER_REGEX
        except Exception:
            pass

    tax_trailing = _YEN_TAX_MARKER_TRAILING_REGEX.search(normalized)
    if tax_trailing:
        try:
            amount = _fix_ocr_price_amount(_normalize_amount(tax_trailing.group('amount')), normalized)
            return amount, 'JPY', _YEN_TAX_MARKER_TRAILING_REGEX
        except Exception:
            pass

    trailing = _TRAILING_AMOUNT_REGEX.search(normalized)
    if trailing:
        amount_raw = trailing.group('amount')
        try:
            amount = _fix_ocr_price_amount(_normalize_amount(amount_raw), normalized)
        except Exception:
            return None
        currency = 'JPY' if _looks_japanese(normalized) else ''
        return amount, currency, _TRAILING_AMOUNT_REGEX

    bare_trailing = _TRAILING_BARE_PRICE_RE.search(normalized)
    if bare_trailing and _looks_japanese(normalized) and _JAN_PRODUCT_CODE_RE.search(normalized):
        try:
            amount = _fix_ocr_price_amount(_normalize_amount(bare_trailing.group('amount')), normalized)
            if Decimal('50') <= amount <= Decimal('50000'):
                return amount, 'JPY', _TRAILING_BARE_PRICE_RE
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
    if _PHONE_LINE_RE.match(normalized.strip()):
        return []
    if _TAX_TARGET_LINE_RE.search(normalized):
        return []

    matched = _match_amount(normalized)
    if not matched:
        return []

    amount, currency, pattern = matched
    return [_build_item(normalized, amount, currency, pattern)]


def _line_has_trailing_price(line: str) -> bool:
    return bool(_PRICE_AT_END_RE.search(_normalize_text(line)))


def _is_register_noise_line(line: str) -> bool:
    normalized = _normalize_text(line)
    if not _REGISTER_NOISE_RE.search(normalized):
        return False
    return not _line_has_trailing_price(normalized)


def split_compound_receipt_line(line: str) -> List[str]:
    """Split Vision OCR lines that concatenate multiple JAN-coded products."""
    normalized = _normalize_text(line).strip()
    if not normalized:
        return []

    codes = _JAN_PRODUCT_CODE_RE.findall(normalized)
    if len(codes) < 2:
        return [normalized]

    segments: List[str] = []
    for match in _JAN_PRODUCT_CODE_RE.finditer(normalized):
        start = match.start()
        next_match = _JAN_PRODUCT_CODE_RE.search(normalized, match.end())
        end = next_match.start() if next_match else len(normalized)
        segment = normalized[start:end].strip()
        if segment:
            segments.append(segment)
    return segments or [normalized]


def preprocess_wrapped_receipt_lines(lines: List[str]) -> List[str]:
    """Join product name lines with the following price line (common on JP receipts)."""
    merged: List[str] = []
    pending: List[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if _is_register_noise_line(line):
            continue
        if _is_receipt_metadata_line(line) or _DATETIME_LINE_REGEX.search(line):
            if pending:
                merged.extend(pending)
                pending = []
            merged.append(line)
            continue
        if _is_receipt_summary_line(line):
            if pending:
                merged.extend(pending)
                pending = []
            merged.append(line)
            continue

        if _line_has_trailing_price(line):
            if pending:
                merged.append(' '.join(pending + [line]))
                pending = []
            else:
                merged.append(line)
        else:
            pending.append(line)

    if pending:
        merged.extend(pending)
    return merged


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

    from services.receipt_formats import parse_receipt_by_format

    items = parse_receipt_by_format(text)

    if not items:
        items = _parse_single_line_shorthand(text)

    if items:
        logger.info(
            'Receipt parser: matched %d item(s): %s',
            len(items),
            ', '.join(f'{it["description"]}={it["amount"]} {it["currency"]}' for it in items[:5]),
        )
    else:
        logger.info('Receipt parser: no expense items matched (text_len=%d)', len(text))

    return items
