from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from jsonschema import Draft7Validator, ValidationError

from services.category_taxonomy import UNKNOWN_CODE, load_category_taxonomy, resolve_code
from services.gemini_client import GeminiClient
from services.log_utils import truncate

logger = logging.getLogger(__name__)

CATEGORIZE_SCHEMA: Dict[str, Any] = {
    'type': 'object',
    'required': ['guessed_category_code', 'alternatives'],
    'properties': {
        'guessed_category_code': {'type': 'string', 'minLength': 1},
        'alternatives': {
            'type': 'array',
            'maxItems': 3,
            'items': {'type': 'string', 'minLength': 1},
        },
    },
    'additionalProperties': False,
}

_validator = Draft7Validator(CATEGORIZE_SCHEMA)
_JSON_FENCE_RE = re.compile(r'^```(?:json)?\s*(.*?)\s*```$', re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class CategoryResult:
    guessed: str
    alternatives: tuple[str, ...]


def _parse_json_object(response: str) -> Any:
    text = response.strip()
    fence_match = _JSON_FENCE_RE.match(text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def _taxonomy_codes_for_prompt() -> str:
    taxonomy = load_category_taxonomy()
    lines = [f'- {code}: {node.name_ja}' for code, node in sorted(taxonomy.items())]
    return '\n'.join(lines)


def validate_categorize_response(data: Any, *, source: str = 'categorize') -> Optional[CategoryResult]:
    if not isinstance(data, dict):
        logger.warning('%s: expected JSON object, got %s', source, type(data).__name__)
        return None

    try:
        _validator.validate(data)
    except ValidationError as exc:
        logger.warning('%s: schema validation failed: %s', source, exc.message)
        return None

    guess = str(data['guessed_category_code']).strip()
    alts_raw = data.get('alternatives') or []
    alts: List[str] = []
    seen = {guess}
    for alt in alts_raw:
        code = str(alt).strip()
        if code and code not in seen:
            alts.append(code)
            seen.add(code)
        if len(alts) >= 3:
            break

    return CategoryResult(guessed=guess, alternatives=tuple(alts))


def normalize_category_result(result: CategoryResult) -> CategoryResult:
    taxonomy = load_category_taxonomy()
    guess_node = resolve_code(result.guessed)
    guess_code = guess_node.code

    alts: List[str] = []
    seen = {guess_code}
    for alt in result.alternatives:
        node = resolve_code(alt)
        if node.code == UNKNOWN_CODE and alt.strip() != UNKNOWN_CODE and alt.strip() not in taxonomy:
            continue
        if node.code not in seen:
            alts.append(node.code)
            seen.add(node.code)
        if len(alts) >= 3:
            break

    return CategoryResult(guessed=guess_code, alternatives=tuple(alts))


async def classify_expense(item: Dict[str, Any], gemini: GeminiClient) -> CategoryResult:
    """Ask Gemini for category JSON only; map invalid codes to unknown."""
    from services.receipt_parser import clean_receipt_description

    raw_description = str(item.get('description', 'Expense')).strip()
    description = clean_receipt_description(raw_description) if raw_description else 'Expense'
    amount = item.get('amount', '')
    currency = item.get('currency', '')

    prompt = (
        'Classify this expense into exactly one category from the predefined taxonomy.\n'
        'Return JSON only with keys guessed_category_code (string) and alternatives (array of 0-3 '
        'distinct category codes excluding the guess).\n'
        'Use only codes from the taxonomy list. Use "unknown" when unsure.\n\n'
        f'Expense: {description} | amount={amount} | currency={currency}\n\n'
        f'Taxonomy codes:\n{_taxonomy_codes_for_prompt()}'
    )

    try:
        response = await gemini.generate_reply(prompt)
        logger.debug('classify_expense raw response: %s', truncate(response or '', 500))
        parsed = _parse_json_object(response)
        validated = validate_categorize_response(parsed, source='classify_expense')
        if validated is None:
            logger.warning('classify_expense: invalid response; using %s', UNKNOWN_CODE)
            return CategoryResult(guessed=UNKNOWN_CODE, alternatives=())
        return normalize_category_result(validated)
    except Exception:
        logger.exception('classify_expense failed for %r', description)
        return CategoryResult(guessed=UNKNOWN_CODE, alternatives=())
