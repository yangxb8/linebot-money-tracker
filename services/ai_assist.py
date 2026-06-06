from typing import List, Dict, Any
import json
import logging

from jsonschema import Draft7Validator, ValidationError

from services.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

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


def validate_expense_items(items: Any) -> List[Dict[str, Any]]:
    """Validate AI-parsed expense items against the expected schema."""
    try:
        _validator.validate(items)
    except ValidationError as exc:
        logger.debug('AI response failed schema validation: %s', exc.message)
        return []

    if not isinstance(items, list):
        return []

    return items


async def assist_parse_ocr(ocr_text: str, gemini: GeminiClient) -> List[Dict[str, Any]]:
    """Call the Gemini client with a minimal prompt to return structured JSON for OCR text."""
    if not ocr_text or not gemini:
        return []

    prompt = (
        'Parse the following OCR text from a receipt into a JSON array of items. '
        'Each item must include: description (string), amount (numeric), currency (3-letter code or symbol). '
        'Return ONLY the JSON array, no other text. OCR_TEXT:\n' + ocr_text
    )

    response = await gemini.generate_reply(prompt)
    try:
        parsed = json.loads(response)
        return validate_expense_items(parsed)
    except json.JSONDecodeError:
        logger.debug('AI response was not valid JSON')
        return []
