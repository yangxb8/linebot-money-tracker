from __future__ import annotations

from typing import Any, Dict, List, Optional


def propagate_receipt_store_name(
    items: List[Dict[str, Any]],
    store_name: Optional[str],
) -> List[Dict[str, Any]]:
    """Apply receipt-level store_name to all line items, or null-out when absent/inconsistent."""
    normalized = str(store_name).strip() if store_name is not None else ''

    if normalized:
        for item in items:
            existing = item.get('store_name')
            if existing is not None and str(existing).strip():
                if str(existing).strip() != normalized:
                    normalized = ''
                    break

    propagated: List[Dict[str, Any]] = []
    for item in items:
        updated = dict(item)
        if normalized:
            updated['store_name'] = normalized
        else:
            updated.pop('store_name', None)
        propagated.append(updated)
    return propagated
