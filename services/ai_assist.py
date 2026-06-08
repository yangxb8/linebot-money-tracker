from typing import List, Dict, Any
import json
import logging
import re

from jsonschema import Draft7Validator, ValidationError

from services.gemini_client import GeminiClient
from services.log_utils import describe_bytes, truncate

logger = logging.getLogger(__name__)

_RECEIPT_ITEM_PROMPT = (
    'Parse this receipt into a JSON array of product/service line items only. '
    'Each item: description (string), amount (number), currency (3-letter code). '
    'Exclude subtotal, tax, total, payment, and change lines. '
    'Per-item amount = final cash-out share: shelf price plus proportional tax, '
    'minus proportional coupons/points USED at payment. Ignore points EARNED (付与). '
    'Item amounts must sum to roughly the final cash paid total (合計/支払). '
    'Return ONLY the JSON array.'
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

_validator = Draft7Validator(EXPENSE_ITEMS_SCHEMA)

_JSON_FENCE_RE = re.compile(r'^```(?:json)?\s*(.*?)\s*```$', re.DOTALL | re.IGNORECASE)


def _parse_json_array(response: str, *, source: str) -> Any:
    text = response.strip()
    fence_match = _JSON_FENCE_RE.match(text)
    if fence_match:
        logger.debug('%s: stripping markdown code fence from response', source)
        text = fence_match.group(1).strip()
    return json.loads(text)


def validate_expense_items(items: Any, *, source: str = 'unknown') -> List[Dict[str, Any]]:
    """Validate AI-parsed expense items against the expected schema."""
    if not isinstance(items, list):
        logger.warning('%s: expected JSON array, got %s', source, type(items).__name__)
        return []

    try:
        _validator.validate(items)
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


async def assist_parse_ocr(ocr_text: str, gemini: GeminiClient) -> List[Dict[str, Any]]:
    """Call the Gemini client with a minimal prompt to return structured JSON for OCR text."""
    source = 'assist_parse_ocr'
    if not ocr_text or not gemini:
        logger.info('%s: skipped (ocr_text=%s gemini=%s)', source, bool(ocr_text), bool(gemini))
        return []

    logger.info('%s: parsing OCR text len=%d', source, len(ocr_text))
    logger.debug('%s OCR text sample: %s', source, truncate(ocr_text, 800))

    prompt = _RECEIPT_ITEM_PROMPT + '\nOCR_TEXT:\n' + ocr_text

    response = await gemini.generate_json_reply(prompt)
    try:
        parsed = _parse_json_array(response, source=source)
        return validate_expense_items(parsed, source=source)
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
) -> List[Dict[str, Any]]:
    """Use Gemini vision to extract expense items directly from a receipt image."""
    source = 'assist_parse_image'
    if not image_bytes or not gemini:
        logger.info(
            '%s: skipped (image=%s gemini=%s)',
            source,
            describe_bytes(image_bytes),
            bool(gemini),
        )
        return []

    logger.info('%s: parsing image=%s mime=%s', source, describe_bytes(image_bytes), mime_type)

    prompt = _RECEIPT_ITEM_PROMPT

    response = await gemini.generate_json_reply_with_image(prompt, image_bytes, mime_type)
    try:
        parsed = _parse_json_array(response, source=source)
        return validate_expense_items(parsed, source=source)
    except json.JSONDecodeError:
        logger.warning(
            '%s: LLM response was not valid JSON: %s',
            source,
            truncate(response, 500),
        )
        return []
