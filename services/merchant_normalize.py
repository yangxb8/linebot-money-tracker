from __future__ import annotations

import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Set

import yaml

logger = logging.getLogger(__name__)

_ALIASES_PATH = Path(__file__).resolve().parent.parent / 'data' / 'merchant_aliases_ja.yaml'

_BRANCH_SUFFIX_RE = re.compile(
    r'(?:\s+|\(|\[|（|【)'
    r'(?:'
    r'[\d０-９]+号店|'
    r'[\w\u3040-\u30ff\u4e00-\u9fff]{1,12}(?:店|支店|駅前店|駅店)|'
    r'駅前|本店|支店'
    r')'
    r'(?:\)|\]|\)|）|】)?\s*$',
    re.IGNORECASE,
)

_GENERIC_DENYLIST: Set[str] = {
    'expense',
    'payment',
    'misc',
    'unknown',
    '不明',
    '食費',
    '買い物',
    '支出',
    '支払',
    '支払い',
    'shopping',
    'grocery',
    'food',
    'lunch',
    'dinner',
    'transport',
}


def _nfkc(text: str) -> str:
    return unicodedata.normalize('NFKC', text or '').strip()


def _ascii_key(text: str) -> str:
    cleaned = re.sub(r'[^a-z0-9]+', '_', text.lower())
    return cleaned.strip('_')


@lru_cache(maxsize=1)
def _load_alias_maps() -> tuple[Dict[str, str], Dict[str, str]]:
    """Return variant→merchant_key and merchant_key→canonical key maps."""
    variant_to_key: Dict[str, str] = {}
    if not _ALIASES_PATH.is_file():
        logger.warning('Merchant alias file missing: %s', _ALIASES_PATH)
        return variant_to_key, {}

    with _ALIASES_PATH.open(encoding='utf-8') as handle:
        raw = yaml.safe_load(handle) or {}

    for merchant_key, variants in raw.items():
        key = str(merchant_key).strip().lower()
        if not key:
            continue
        variant_to_key[_nfkc(key).lower()] = key
        for variant in variants or []:
            normalized = _nfkc(str(variant)).lower()
            if normalized:
                variant_to_key[normalized] = key
    return variant_to_key, {k: k for k in raw.keys()}


def is_generic_merchant_text(text: str) -> bool:
    normalized = _nfkc(text).lower()
    if not normalized or len(normalized) < 2:
        return True
    if normalized in _GENERIC_DENYLIST:
        return True
    compact = re.sub(r'\s+', '', normalized)
    return compact in _GENERIC_DENYLIST


def strip_branch_suffix(text: str) -> str:
    cleaned = _nfkc(text)
    previous = None
    while cleaned and cleaned != previous:
        previous = cleaned
        cleaned = _BRANCH_SUFFIX_RE.sub('', cleaned).strip(' -@:，、.')
    return cleaned


def _match_alias(text: str) -> Optional[str]:
    variant_to_key, _ = _load_alias_maps()
    normalized = _nfkc(text).lower()
    if not normalized:
        return None

    if normalized in variant_to_key:
        return variant_to_key[normalized]

    compact = re.sub(r'[\s\-・.]+', '', normalized)
    for variant, key in variant_to_key.items():
        variant_compact = re.sub(r'[\s\-・.]+', '', variant)
        if not variant_compact:
            continue
        if variant_compact in compact or compact in variant_compact:
            if len(variant_compact) >= 3 or len(compact) >= 3:
                return key
    return None


def normalize_merchant_key(raw_merchant: Optional[str]) -> Optional[str]:
    """Normalize extracted merchant name to canonical merchant_key."""
    if raw_merchant is None:
        return None

    stripped = strip_branch_suffix(str(raw_merchant))
    if is_generic_merchant_text(stripped):
        return None

    alias_key = _match_alias(stripped)
    if alias_key:
        return alias_key

    ascii_key = _ascii_key(stripped)
    if not ascii_key or len(ascii_key) < 2:
        return None
    if is_generic_merchant_text(ascii_key):
        return None
    return ascii_key


def heuristic_merchant_from_description(description: str) -> Optional[str]:
    """Rule-based merchant key for backfill without LLM."""
    from services.receipt_parser import clean_receipt_description

    cleaned = clean_receipt_description(description or '')
    if is_generic_merchant_text(cleaned):
        return None

    alias_key = _match_alias(cleaned)
    if alias_key:
        return alias_key

    first_chunk = strip_branch_suffix(cleaned.split('|')[0].split('/')[0].strip())
    alias_key = _match_alias(first_chunk)
    if alias_key:
        return alias_key

    token = first_chunk.split()[0] if first_chunk.split() else first_chunk
    return normalize_merchant_key(token)


def reset_merchant_alias_cache_for_tests() -> None:
    _load_alias_maps.cache_clear()
