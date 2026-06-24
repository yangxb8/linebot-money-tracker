#!/usr/bin/env python3
"""Backfill category_merchant_memory from historical expenses (no LLM)."""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple

from services.category_taxonomy import load_category_taxonomy_for_tenant, resolve_code
from services.merchant_normalize import heuristic_merchant_from_description
from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOURCE_BACKFILL = 'backfill'


def _category_code_for_expense(row: dict) -> str | None:
    tenant = TenantContext(
        tenant_type=str(row['tenant_type']),
        tenant_id=str(row['tenant_id']),
        logged_by_line_user_id=str(row.get('logged_by_line_user_id') or row['tenant_id']),
    )
    taxonomy = load_category_taxonomy_for_tenant(tenant)
    node_id = str(row.get('category_node_id') or '')
    for node in taxonomy.values():
        if node.id == node_id:
            return node.code
    return None


def collect_backfill_rows() -> Dict[Tuple[str, str, str], dict]:
    if not is_supabase_configured():
        raise RuntimeError('Supabase not configured')

    client = get_supabase_client()
    response = (
        client.table('expenses')
        .select(
            'tenant_type, tenant_id, logged_by_line_user_id, description, '
            'category_node_id, created_at'
        )
        .is_('deleted_at', 'null')
        .order('created_at')
        .execute()
    )
    rows = response.data or []

    grouped: Dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
    for row in rows:
        merchant_key = heuristic_merchant_from_description(str(row.get('description', '')))
        if not merchant_key:
            continue
        category_code = _category_code_for_expense(row)
        if not category_code:
            continue
        key = (str(row['tenant_type']), str(row['tenant_id']), merchant_key)
        grouped[key].append({**row, 'category_code': category_code, 'merchant_key': merchant_key})

    result: Dict[Tuple[str, str, str], dict] = {}
    for key, items in grouped.items():
        last = items[-1]
        same_category_count = sum(1 for item in items if item['category_code'] == last['category_code'])
        weight = min(Decimal('1.0'), Decimal('0.25') + Decimal('0.5') * max(same_category_count - 1, 0))
        result[key] = {
            'tenant_type': key[0],
            'tenant_id': key[1],
            'merchant_key': key[2],
            'category_code': last['category_code'],
            'weight': float(weight),
            'display_merchant': str(last.get('description', ''))[:120],
            'sample_description': str(last.get('description', ''))[:200],
            'hit_count': same_category_count,
            'last_source': SOURCE_BACKFILL,
        }
    return result


def upsert_rows(rows: Dict[Tuple[str, str, str], dict], *, dry_run: bool) -> int:
    if dry_run:
        logger.info('Dry run: would upsert %d memory rows', len(rows))
        return len(rows)

    client = get_supabase_client()
    count = 0
    for payload in rows.values():
        existing = (
            client.table('category_merchant_memory')
            .select('id')
            .eq('tenant_type', payload['tenant_type'])
            .eq('tenant_id', payload['tenant_id'])
            .eq('merchant_key', payload['merchant_key'])
            .limit(1)
            .execute()
        ).data or []
        if existing:
            client.table('category_merchant_memory').update(payload).eq('id', existing[0]['id']).execute()
        else:
            client.table('category_merchant_memory').insert(payload).execute()
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description='Backfill tenant category merchant memory')
    parser.add_argument('--dry-run', action='store_true', help='Print counts without writing')
    args = parser.parse_args()

    rows = collect_backfill_rows()
    written = upsert_rows(rows, dry_run=args.dry_run)
    logger.info('Processed %d merchant memory rows', written)


if __name__ == '__main__':
    main()
