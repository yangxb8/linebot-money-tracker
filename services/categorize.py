from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from jsonschema import Draft7Validator, ValidationError

from services.category_taxonomy import UNKNOWN_CODE, load_category_taxonomy_for_tenant, resolve_code
from services.gemini_client import GeminiClient
from services.tenant_context import TenantContext
from services.log_utils import truncate
from services.usage_metering import llm_operation_scope

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


@dataclass(frozen=True)
class CategoryResultWithProvenance:
    guessed: str
    alternatives: tuple[str, ...]
    source: Literal['memory', 'item_memory', 'llm']
    merchant_key: Optional[str] = None
    display_merchant: Optional[str] = None
    item_key: Optional[str] = None
    item_memory_kind: Optional[Literal['store_item', 'item_only']] = None


def _parse_json_object(response: str) -> Any:
    text = response.strip()
    fence_match = _JSON_FENCE_RE.match(text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def _taxonomy_codes_for_prompt(tenant: Optional[TenantContext] = None) -> str:
    taxonomy = load_category_taxonomy_for_tenant(tenant)
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


def normalize_category_result(
    result: CategoryResult,
    tenant: Optional[TenantContext] = None,
) -> CategoryResult:
    taxonomy = load_category_taxonomy_for_tenant(tenant)
    guess_node = resolve_code(result.guessed, tenant)
    guess_code = guess_node.code

    alts: List[str] = []
    seen = {guess_code}
    for alt in result.alternatives:
        node = resolve_code(alt, tenant)
        if node.code == UNKNOWN_CODE and alt.strip() != UNKNOWN_CODE and alt.strip() not in taxonomy:
            continue
        if node.code not in seen:
            alts.append(node.code)
            seen.add(node.code)
        if len(alts) >= 3:
            break

    return CategoryResult(guessed=guess_code, alternatives=tuple(alts))


CATEGORY_MAP_SCHEMA: Dict[str, Any] = {
    'type': 'object',
    'required': ['options'],
    'properties': {
        'options': {
            'type': 'array',
            'maxItems': 3,
            'items': {'type': 'string', 'minLength': 1},
        },
    },
    'additionalProperties': False,
}

_category_map_validator = Draft7Validator(CATEGORY_MAP_SCHEMA)


def validate_category_map_response(
    data: Any,
    *,
    source: str = 'category_map',
    tenant: Optional[TenantContext] = None,
) -> tuple[str, ...]:
    if not isinstance(data, dict):
        logger.warning('%s: expected JSON object, got %s', source, type(data).__name__)
        return ()

    try:
        _category_map_validator.validate(data)
    except ValidationError as exc:
        logger.warning('%s: schema validation failed: %s', source, exc.message)
        return ()

    taxonomy = load_category_taxonomy_for_tenant(tenant)
    options: List[str] = []
    seen: set[str] = set()
    for raw in data.get('options') or []:
        code = str(raw).strip()
        if not code:
            continue
        node = resolve_code(code, tenant)
        if node.code == UNKNOWN_CODE and code != UNKNOWN_CODE and code not in taxonomy:
            continue
        if node.code in seen:
            continue
        options.append(node.code)
        seen.add(node.code)
        if len(options) >= 3:
            break
    return tuple(options)


async def map_category_from_text(
    user_text: str,
    gemini: GeminiClient,
    *,
    tenant: Optional[TenantContext] = None,
) -> tuple[str, ...]:
    """Map free-text category phrase to up to 3 taxonomy codes."""
    query = (user_text or '').strip()
    if not query:
        return ()

    prompt = (
        'Map the user category phrase to up to 3 matching codes from the predefined taxonomy.\n'
        'Return JSON only with key options (array of 0-3 distinct category codes).\n'
        'Order by best match first. Use only codes from the taxonomy list.\n\n'
        f'User category phrase: {query}\n\n'
        f'Taxonomy codes:\n{_taxonomy_codes_for_prompt(tenant)}'
    )

    try:
        with llm_operation_scope('categorize'):
            response = await gemini.generate_reply(prompt)
        logger.debug('map_category_from_text raw response: %s', truncate(response or '', 500))
        parsed = _parse_json_object(response)
        return validate_category_map_response(
            parsed,
            source='map_category_from_text',
            tenant=tenant,
        )
    except Exception:
        logger.exception('map_category_from_text failed for %r', query)
        return ()


async def classify_expense_with_memory(
    item: Dict[str, Any],
    gemini: GeminiClient,
    *,
    tenant: Optional[TenantContext] = None,
    exclude_source_message_id: Optional[str] = None,
    memory_mode: Literal['merchant', 'item'] = 'merchant',
) -> CategoryResultWithProvenance:
    from services.category_memory import (
        MEMORY_SKIP_WEIGHT_THRESHOLD,
        apply_item_silent_confirm,
        apply_silent_confirm,
        expense_category_code,
        expense_guess_unchanged,
        find_prior_expense_for_merchant,
        find_prior_expense_for_store_item,
        lookup_item_memory,
        lookup_memory,
        memory_category_is_valid,
        upsert_item_llm_seed,
        upsert_llm_seed,
    )
    from services.item_normalize import normalize_item_key
    from services.merchant_resolve import resolve_raw_merchant
    from services.receipt_parser import clean_receipt_description

    raw_description = str(item.get('description', 'Expense')).strip()
    description = clean_receipt_description(raw_description) if raw_description else 'Expense'

    raw_merchant, merchant_key = await resolve_raw_merchant(item, gemini)

    if memory_mode == 'item':
        item_key = normalize_item_key(description)

        if tenant is not None and item_key and merchant_key:
            prior = find_prior_expense_for_store_item(
                tenant,
                merchant_key,
                item_key,
                exclude_source_message_id=exclude_source_message_id,
            )
            if prior is not None and expense_guess_unchanged(prior, tenant):
                prior_code = expense_category_code(prior, tenant)
                if prior_code:
                    apply_item_silent_confirm(
                        tenant,
                        merchant_key=merchant_key,
                        item_key=item_key,
                        category_code=prior_code,
                        display_merchant=raw_merchant,
                        sample_description=description,
                    )

        if tenant is not None and item_key:
            store_hit = None
            if merchant_key:
                store_hit = lookup_item_memory(
                    tenant,
                    memory_kind='store_item',
                    merchant_key=merchant_key,
                    item_key=item_key,
                )
            item_only_hit = None
            if store_hit is None:
                item_only_hit = lookup_item_memory(
                    tenant,
                    memory_kind='item_only',
                    item_key=item_key,
                )

            hit = store_hit or item_only_hit
            if (
                hit is not None
                and hit.weight >= MEMORY_SKIP_WEIGHT_THRESHOLD
                and memory_category_is_valid(hit.category_code, tenant)
            ):
                logger.info(
                    'item_memory hit kind=%s item_key=%s merchant_key=%s',
                    hit.memory_kind,
                    item_key,
                    merchant_key,
                )
                return CategoryResultWithProvenance(
                    guessed=hit.category_code,
                    alternatives=(),
                    source='item_memory',
                    merchant_key=merchant_key,
                    display_merchant=raw_merchant or hit.display_merchant,
                    item_key=item_key,
                    item_memory_kind=hit.memory_kind,
                )

        category_hint: Optional[str] = None
        if merchant_key and tenant is not None:
            merchant_mem = lookup_memory(tenant, merchant_key)
            if merchant_mem is not None and memory_category_is_valid(
                merchant_mem.category_code, tenant
            ):
                category_hint = merchant_mem.category_code

        logger.info(
            'item_memory miss soft_prior=%s item_key=%s merchant_key=%s',
            bool(category_hint),
            item_key,
            merchant_key,
        )
        llm_result = await classify_expense(
            item,
            gemini,
            tenant=tenant,
            category_hint=category_hint,
        )

        if merchant_key and item_key and tenant is not None:
            upsert_item_llm_seed(
                tenant,
                merchant_key=merchant_key,
                item_key=item_key,
                category_code=llm_result.guessed,
                display_merchant=raw_merchant,
                sample_description=description,
            )

        return CategoryResultWithProvenance(
            guessed=llm_result.guessed,
            alternatives=llm_result.alternatives,
            source='llm',
            merchant_key=merchant_key,
            display_merchant=raw_merchant,
            item_key=item_key,
        )

    # --- merchant mode (013 text path) ---
    if merchant_key and tenant is not None:
        prior = find_prior_expense_for_merchant(
            tenant,
            merchant_key,
            exclude_source_message_id=exclude_source_message_id,
        )
        if prior is not None and expense_guess_unchanged(prior, tenant):
            prior_code = expense_category_code(prior, tenant)
            if prior_code:
                apply_silent_confirm(
                    tenant,
                    merchant_key=merchant_key,
                    category_code=prior_code,
                    display_merchant=raw_merchant,
                    sample_description=description,
                )

        memory = lookup_memory(tenant, merchant_key)
        if (
            memory is not None
            and memory.weight >= MEMORY_SKIP_WEIGHT_THRESHOLD
            and memory_category_is_valid(memory.category_code, tenant)
        ):
            return CategoryResultWithProvenance(
                guessed=memory.category_code,
                alternatives=(),
                source='memory',
                merchant_key=merchant_key,
                display_merchant=raw_merchant or memory.display_merchant,
            )

    llm_result = await classify_expense(item, gemini, tenant=tenant)

    if merchant_key and tenant is not None:
        upsert_llm_seed(
            tenant,
            merchant_key=merchant_key,
            category_code=llm_result.guessed,
            display_merchant=raw_merchant,
            sample_description=description,
        )

    return CategoryResultWithProvenance(
        guessed=llm_result.guessed,
        alternatives=llm_result.alternatives,
        source='llm',
        merchant_key=merchant_key,
        display_merchant=raw_merchant,
    )


async def classify_expense(
    item: Dict[str, Any],
    gemini: GeminiClient,
    *,
    tenant: Optional[TenantContext] = None,
    category_hint: Optional[str] = None,
) -> CategoryResult:
    """Ask Gemini for category JSON only; map invalid codes to unknown."""
    from services.receipt_parser import clean_receipt_description

    raw_description = str(item.get('description', 'Expense')).strip()
    description = clean_receipt_description(raw_description) if raw_description else 'Expense'
    amount = item.get('amount', '')
    currency = item.get('currency', '')

    hint_block = ''
    if category_hint:
        hint_node = resolve_code(category_hint, tenant)
        hint_block = (
            f'Merchant is often categorized as {hint_node.code} ({hint_node.name_ja}). '
            'Use that only as a soft prior; choose the best code for THIS line item, '
            'which may differ.\n\n'
        )

    prompt = (
        'Classify this expense into exactly one category from the predefined taxonomy.\n'
        'Return JSON only with keys guessed_category_code (string) and alternatives (array of 0-3 '
        'distinct category codes excluding the guess).\n'
        'Use only codes from the taxonomy list. Use "unknown" when unsure.\n\n'
        f'{hint_block}'
        f'Expense: {description} | amount={amount} | currency={currency}\n\n'
        f'Taxonomy codes:\n{_taxonomy_codes_for_prompt(tenant)}'
    )

    try:
        with llm_operation_scope('categorize'):
            response = await gemini.generate_reply(prompt)
        logger.debug('classify_expense raw response: %s', truncate(response or '', 500))
        parsed = _parse_json_object(response)
        validated = validate_categorize_response(parsed, source='classify_expense')
        if validated is None:
            logger.warning('classify_expense: invalid response; using %s', UNKNOWN_CODE)
            return CategoryResult(guessed=UNKNOWN_CODE, alternatives=())
        return normalize_category_result(validated, tenant)
    except Exception:
        logger.exception('classify_expense failed for %r', description)
        return CategoryResult(guessed=UNKNOWN_CODE, alternatives=())
