from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict, Any, Optional
import json
import logging
import re

from jsonschema import Draft7Validator, ValidationError

from services.gemini_client import GeminiClient
from services.log_utils import describe_bytes, truncate
from services.usage_metering import llm_operation_scope

logger = logging.getLogger(__name__)

_TEXT_EXPENSE_PROMPT = (
    'Parse this chat message as a personal expense log. The user is recording money they spent.\n'
    'Return a JSON array of line items. Each item: description (string), amount (number), currency (3-letter code).\n'
    'Infer JPY when the message uses Japanese/Chinese and no currency is stated.\n'
    'If the message is a question, brand lookup, or cannot be interpreted as logging an expense, return [].\n'
    'Return ONLY the JSON array.'
)

# Legacy OCR-text assist prompt (kept for future OCR pipeline).
_RECEIPT_ITEM_PROMPT = (
    'Parse this receipt into a JSON array of product/service line items only. '
    'Each item: description (string), amount (number), currency (3-letter code). '
    'Exclude subtotal, tax, total, payment, change, and card-slip lines. '
    'Per-item amount = SHELF / TAG price on the receipt line (before tax allocation). '
    'Do NOT include tax, discounts, or card-authorization numbers as amounts. '
    'Typical Japanese snack items are tens to hundreds of yen, not thousands. '
    'Ignore points EARNED (付与). Return ONLY the JSON array.'
)

_RECEIPT_IMAGE_PROMPT = (
    'Parse this receipt image into a JSON object with four fields:\n'
    '- "store_name": the store/merchant/chain name from the receipt header or register '
    'banner (string or null). NOT a product name. Examples: イオン, セブン-イレブン, マツモトキヨシ, ロピア.\n'
    '- "items": array of product/service line items only. Each item has '
    'description (string), amount (number), currency (3-letter code).\n'
    '- "total": the receipt final cash total (合計 / amount paid), as a number.\n'
    '- "currency": 3-letter code for the receipt total.\n\n'
    'Rules:\n'
    '- Extract EVERY product/service row on the receipt — do not omit lines for brevity.\n'
    '- Per-item amount = tax-inclusive cash-out for that line (line total including tax). '
    'Item amounts MUST sum to "total" within ¥2.\n'
    '- Exclude subtotal (小計), tax breakdown, payment (支払), change, points, and '
    'card-slip lines from items. Never invent a filler item to force the sum.\n'
    '- Include quantity line totals as one item per product (e.g. 6×¥100 → amount 600).\n'
    '- Include bags and low-value items (≥ ¥1). Grocery/meat/alcohol lines may be '
    'hundreds to thousands of yen — keep them.\n'
    '- Ignore points EARNED (付与); points USED reduce the cash total only.\n'
    'Return ONLY the JSON object.'
)

_RECEIPT_IMAGE_RETRY_PROMPT = (
    _RECEIPT_IMAGE_PROMPT
    + '\nIMPORTANT RETRY: A previous parse of this same image failed validation because '
    'product line amounts did not sum to the receipt total (items were incomplete or '
    'included non-product lines). Re-read the full receipt carefully and return every '
    'product line so tax-inclusive amounts sum to "total".'
)

EXPENSE_ITEMS_SCHEMA: Dict[str, Any] = {
    'type': 'array',
    'items': {
        'type': 'object',
        'required': ['description', 'amount', 'currency'],
        'properties': {
            'description': {'type': 'string', 'minLength': 1},
            'amount': {'type': 'number'},
            'currency': {'type': 'string', 'minLength': 1},
        },
        'additionalProperties': True,
    },
}

RECEIPT_IMAGE_PARSE_SCHEMA: Dict[str, Any] = {
    'type': 'object',
    'required': ['items', 'total', 'currency'],
    'properties': {
        'store_name': {
            'anyOf': [
                {'type': 'string', 'minLength': 1},
                {'type': 'null'},
            ],
        },
        'items': EXPENSE_ITEMS_SCHEMA,
        'total': {'type': 'number'},
        'currency': {'type': 'string', 'minLength': 1},
    },
    'additionalProperties': True,
}

_items_validator = Draft7Validator(EXPENSE_ITEMS_SCHEMA)
_image_parse_validator = Draft7Validator(RECEIPT_IMAGE_PARSE_SCHEMA)

_JSON_FENCE_RE = re.compile(r'^```(?:json)?\s*(.*?)\s*```$', re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class ReceiptImageParseResult:
    items: List[Dict[str, Any]]
    total: Decimal
    currency: str
    store_name: Optional[str] = None


def _strip_json_fence(response: str) -> str:
    text = response.strip()
    fence_match = _JSON_FENCE_RE.match(text)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _parse_json(response: str, *, source: str) -> Any:
    text = _strip_json_fence(response)
    return json.loads(text)


def validate_expense_items(items: Any, *, source: str = 'unknown') -> List[Dict[str, Any]]:
    """Validate AI-parsed expense items against the expected schema."""
    if not isinstance(items, list):
        logger.warning('%s: expected JSON array, got %s', source, type(items).__name__)
        return []

    try:
        _items_validator.validate(items)
    except ValidationError as exc:
        logger.warning(
            '%s: schema validation failed at %s: %s',
            source,
            '/'.join(str(p) for p in exc.path) or 'root',
            exc.message,
        )
        return []

    logger.info('%s: validated %d expense item(s)', source, len(items))
    for idx, item in enumerate(items[:5]):
        logger.debug(
            '%s item[%d]: description=%r amount=%s currency=%s',
            source,
            idx,
            item.get('description'),
            item.get('amount'),
            item.get('currency'),
        )
    return items


def validate_receipt_image_parse(
    parsed: Any,
    *,
    source: str = 'unknown',
) -> Optional[ReceiptImageParseResult]:
    """Validate vision LLM receipt parse (items + total wrapper)."""
    if not isinstance(parsed, dict):
        logger.warning('%s: expected JSON object, got %s', source, type(parsed).__name__)
        return None

    try:
        _image_parse_validator.validate(parsed)
    except ValidationError as exc:
        logger.warning(
            '%s: schema validation failed at %s: %s',
            source,
            '/'.join(str(p) for p in exc.path) or 'root',
            exc.message,
        )
        return None

    items = validate_expense_items(parsed.get('items'), source=source)
    if not items:
        return None

    try:
        total = Decimal(str(parsed['total'])).quantize(Decimal('0.01'))
    except Exception:
        logger.warning('%s: invalid total value %r', source, parsed.get('total'))
        return None

    if total <= 0:
        logger.warning('%s: total must be positive, got %s', source, total)
        return None

    currency = str(parsed.get('currency', '')).strip().upper()
    if not currency:
        logger.warning('%s: missing currency on receipt parse', source)
        return None

    store_name: Optional[str] = None
    raw_store = parsed.get('store_name')
    if raw_store is not None:
        stripped = str(raw_store).strip()
        if stripped:
            store_name = stripped

    logger.info(
        '%s: validated %d item(s) total=%s %s store_name=%r',
        source,
        len(items),
        total,
        currency,
        store_name,
    )
    return ReceiptImageParseResult(
        items=items,
        total=total,
        currency=currency,
        store_name=store_name,
    )


async def assist_parse_text(text: str, gemini: GeminiClient) -> List[Dict[str, Any]]:
    """Structured LLM assist for free-form expense text when the deterministic parser fails."""
    source = 'assist_parse_text'
    if not text or not gemini:
        logger.info('%s: skipped (text=%s gemini=%s)', source, bool(text), bool(gemini))
        return []

    normalized = text.strip()
    if not normalized:
        logger.info('%s: skipped (blank after strip)', source)
        return []

    logger.info('%s: parsing text len=%d', source, len(normalized))
    logger.debug('%s text sample: %s', source, truncate(normalized, 500))

    prompt = _TEXT_EXPENSE_PROMPT + '\nMessage:\n' + normalized

    with llm_operation_scope('assist'):
        response = await gemini.generate_json_reply(prompt)
    try:
        parsed = _parse_json(response, source=source)
        if isinstance(parsed, list):
            return validate_expense_items(parsed, source=source)
        logger.warning('%s: expected JSON array from text assist', source)
        return []
    except json.JSONDecodeError:
        logger.warning(
            '%s: LLM response was not valid JSON: %s',
            source,
            truncate(response, 500),
        )
        return []


async def assist_parse_ocr(ocr_text: str, gemini: GeminiClient) -> List[Dict[str, Any]]:
    """Call the Gemini client with a minimal prompt to return structured JSON for OCR text."""
    source = 'assist_parse_ocr'
    if not ocr_text or not gemini:
        logger.info('%s: skipped (ocr_text=%s gemini=%s)', source, bool(ocr_text), bool(gemini))
        return []

    logger.info('%s: parsing OCR text len=%d', source, len(ocr_text))
    logger.debug('%s OCR text sample: %s', source, truncate(ocr_text, 800))

    prompt = _RECEIPT_ITEM_PROMPT + '\nOCR_TEXT:\n' + ocr_text

    with llm_operation_scope('assist'):
        response = await gemini.generate_json_reply(prompt)
    try:
        parsed = _parse_json(response, source=source)
        if isinstance(parsed, list):
            return validate_expense_items(parsed, source=source)
        logger.warning('%s: expected JSON array from OCR assist', source)
        return []
    except json.JSONDecodeError:
        logger.warning(
            '%s: LLM response was not valid JSON: %s',
            source,
            truncate(response, 500),
        )
        return []


async def assist_parse_image(
    image_bytes: bytes,
    gemini: GeminiClient,
    mime_type: str = 'image/jpeg',
    *,
    retry: bool = False,
) -> Optional[ReceiptImageParseResult]:
    """Use Gemini vision to extract expense items and receipt total from an image."""
    source = 'assist_parse_image_retry' if retry else 'assist_parse_image'
    if not image_bytes or not gemini:
        logger.info(
            '%s: skipped (image=%s gemini=%s)',
            source,
            describe_bytes(image_bytes),
            bool(gemini),
        )
        return None

    prompt = _RECEIPT_IMAGE_RETRY_PROMPT if retry else _RECEIPT_IMAGE_PROMPT
    logger.info(
        '%s: parsing image=%s mime=%s retry=%s',
        source,
        describe_bytes(image_bytes),
        mime_type,
        retry,
    )

    response = await gemini.generate_json_reply_with_image(prompt, image_bytes, mime_type)
    try:
        parsed = _parse_json(response, source=source)
        result = validate_receipt_image_parse(parsed, source=source)
        if result is None:
            logger.warning(
                '%s: schema/item validation failed; response=%s',
                source,
                truncate(response, 800),
            )
        return result
    except json.JSONDecodeError:
        logger.warning(
            '%s: LLM response was not valid JSON: %s',
            source,
            truncate(response, 800),
        )
        return None
