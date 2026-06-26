from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from services.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


def merchant_key_from_expense_row(row: Dict[str, Any]) -> Optional[str]:
    """Prefer metadata.store_name over description heuristic for backfill and prior-expense lookup."""
    from services.merchant_normalize import (
        heuristic_merchant_from_description,
        is_generic_merchant_text,
        normalize_merchant_key,
        strip_branch_suffix,
    )

    metadata = row.get('metadata') or {}
    if isinstance(metadata, dict):
        store_raw = metadata.get('store_name')
        if store_raw is not None and str(store_raw).strip():
            raw = strip_branch_suffix(str(store_raw).strip())
            if raw and not is_generic_merchant_text(raw):
                key = normalize_merchant_key(raw)
                if key:
                    return key

    return heuristic_merchant_from_description(str(row.get('description', '')))


async def resolve_raw_merchant(
    item: Dict[str, Any],
    gemini: GeminiClient,
) -> Tuple[Optional[str], Optional[str]]:
    """Return (raw_merchant, merchant_key). Skips merchant LLM when store_name normalizes."""
    from services.merchant_extract import extract_merchant_name
    from services.merchant_normalize import (
        is_generic_merchant_text,
        normalize_merchant_key,
        strip_branch_suffix,
    )
    from services.receipt_parser import clean_receipt_description

    raw_description = str(item.get('description', 'Expense')).strip()
    description = clean_receipt_description(raw_description) if raw_description else 'Expense'
    amount = item.get('amount', '')
    currency = item.get('currency', '')

    store_raw = item.get('store_name')
    if store_raw is not None and str(store_raw).strip():
        raw_merchant = strip_branch_suffix(str(store_raw).strip())
        if raw_merchant and not is_generic_merchant_text(raw_merchant):
            merchant_key = normalize_merchant_key(raw_merchant)
            if merchant_key:
                logger.info(
                    'merchant_resolve: source=store_name key=%s raw=%s',
                    merchant_key,
                    raw_merchant,
                )
                return raw_merchant, merchant_key
            logger.info(
                'merchant_resolve: source=description (store_name normalize failed) raw=%s',
                raw_merchant,
            )

    raw_merchant = await extract_merchant_name(
        description,
        gemini,
        amount=amount,
        currency=currency,
    )
    merchant_key = normalize_merchant_key(raw_merchant)
    if merchant_key:
        logger.info('merchant_resolve: source=description key=%s', merchant_key)
    return raw_merchant, merchant_key
