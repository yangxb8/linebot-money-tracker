from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from jsonschema import Draft7Validator, ValidationError

from services.gemini_client import GeminiClient
from services.log_utils import truncate
from services.merchant_normalize import is_generic_merchant_text, strip_branch_suffix
from services.usage_metering import llm_operation_scope

logger = logging.getLogger(__name__)

MERCHANT_EXTRACT_SCHEMA: Dict[str, Any] = {
    'type': 'object',
    'required': ['merchant_name'],
    'properties': {
        'merchant_name': {
            'anyOf': [
                {'type': 'string', 'minLength': 1},
                {'type': 'null'},
            ],
        },
    },
    'additionalProperties': False,
}

_validator = Draft7Validator(MERCHANT_EXTRACT_SCHEMA)
_JSON_FENCE_RE = re.compile(r'^```(?:json)?\s*(.*?)\s*```$', re.DOTALL | re.IGNORECASE)


def _parse_json_object(response: str) -> Any:
    text = response.strip()
    fence_match = _JSON_FENCE_RE.match(text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def validate_merchant_extract_response(data: Any) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    try:
        _validator.validate(data)
    except ValidationError:
        return None

    raw = data.get('merchant_name')
    if raw is None:
        return None
    merchant = strip_branch_suffix(str(raw))
    if not merchant or is_generic_merchant_text(merchant):
        return None
    return merchant


async def extract_merchant_name(
    description: str,
    gemini: GeminiClient,
    *,
    amount: Any = '',
    currency: str = '',
) -> Optional[str]:
    """LLM extraction of store/brand/merchant from expense description."""
    from services.receipt_parser import clean_receipt_description

    cleaned = clean_receipt_description(description or '')
    if not cleaned or is_generic_merchant_text(cleaned):
        return None

    prompt = (
        'Extract the store, brand, or merchant name from this expense description.\n'
        'Return JSON only: {"merchant_name": string | null}.\n'
        'Return the seller/merchant, not the product name when both are present.\n'
        'Return null for generic descriptions (e.g. 食費, 買い物, payment, expense).\n\n'
        f'Description: {cleaned}\n'
        f'Amount: {amount}\n'
        f'Currency: {currency}'
    )

    try:
        with llm_operation_scope('merchant_extract'):
            response = await gemini.generate_reply(prompt)
        logger.debug('extract_merchant_name raw response: %s', truncate(response or '', 500))
        parsed = _parse_json_object(response)
        return validate_merchant_extract_response(parsed)
    except Exception:
        logger.exception('extract_merchant_name failed for %r', cleaned)
        return None
