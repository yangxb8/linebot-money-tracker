"""Deterministic item_key normalization for receipt item memory (feature 018).

See specs/018-item-category-memory/contracts/item-normalize.md
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Set

from services.receipt_parser import clean_receipt_description

_GENERIC_DENYLIST: Set[str] = {
    '商品',
    '不明',
    '税',
    '合計',
    '小计',
    '小計',
    'expense',
    'item',
    'product',
    'misc',
    'unknown',
    'payment',
    '買い物',
    '食費',
}

_SIZE_MODEL_RE = re.compile(
    r'(?i)(?:\bW\d+\b|\b[A-Z]\b(?=\s|$)|ロール+\w*|@\s*\d+|\d+\s*[個本枚入袋組缶ケースパック巻卷]?)'
)
_NON_KEY_CHARS_RE = re.compile(r'[^\w\u3040-\u30ff\u3400-\u9fff]+', re.UNICODE)
_HAS_CJK_RE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')
_HAS_ASCII_ALNUM_RE = re.compile(r'[A-Za-z0-9]')


def normalize_item_key(description: Optional[str]) -> Optional[str]:
    """Return stable item_key or None when generic / empty."""
    if description is None:
        return None
    cleaned = clean_receipt_description(str(description))
    if not cleaned or cleaned == 'Expense':
        return None

    text = unicodedata.normalize('NFKC', cleaned).strip()
    # Strip size/pack/model tokens iteratively
    previous = None
    while text and text != previous:
        previous = text
        text = _SIZE_MODEL_RE.sub(' ', text)
        text = re.sub(r'\s+', ' ', text).strip(' -@:，、.')

    text = _NON_KEY_CHARS_RE.sub(' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return None

    compact_check = re.sub(r'\s+', '', text).lower()
    if compact_check in _GENERIC_DENYLIST or text.lower() in _GENERIC_DENYLIST:
        return None
    if len(compact_check) < 2:
        return None

    has_cjk = bool(_HAS_CJK_RE.search(text))
    has_ascii = bool(_HAS_ASCII_ALNUM_RE.search(text))

    if has_cjk and not has_ascii:
        return re.sub(r'\s+', '', text)

    if has_cjk and has_ascii:
        # Keep CJK contiguous; lowercase ASCII tokens joined with _
        parts: list[str] = []
        for token in text.split():
            if _HAS_CJK_RE.search(token) and not _HAS_ASCII_ALNUM_RE.search(token):
                parts.append(token)
            elif _HAS_CJK_RE.search(token):
                # mixed token: strip non-alnum keep as-is lower ascii letters
                mixed = re.sub(r'[^0-9A-Za-z\u3040-\u30ff\u3400-\u9fff]', '', token)
                parts.append(mixed.lower() if mixed.isascii() else mixed)
            else:
                parts.append(token.lower())
        key = '_'.join(p for p in parts if p)
        return key or None

    # ASCII-only
    tokens = [t.lower() for t in text.split() if t]
    key = '_'.join(tokens)
    if not key or len(key) < 2 or key in _GENERIC_DENYLIST:
        return None
    return key
