from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from services.category_taxonomy import load_category_taxonomy_for_tenant, resolve_code
from services.gemini_client import GeminiClient
from services.merchant_normalize import heuristic_merchant_from_description, normalize_merchant_key
from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)

JST = ZoneInfo('Asia/Tokyo')

MEMORY_SKIP_WEIGHT_THRESHOLD = Decimal('1.0')
WEIGHT_LLM_SEED = Decimal('0.25')
WEIGHT_SILENT_CONFIRM = Decimal('0.5')
WEIGHT_USER_CORRECTION = Decimal('1.0')

SOURCE_LLM = 'llm'
SOURCE_USER_CORRECTION = 'user_correction'
SOURCE_SILENT_CONFIRM = 'silent_confirm'
SOURCE_BACKFILL = 'backfill'


@dataclass(frozen=True)
class MemoryRow:
    merchant_key: str
    category_code: str
    weight: Decimal
    display_merchant: Optional[str] = None


def _now_iso() -> str:
    return datetime.now(JST).isoformat()


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value if value is not None else 0))
    except Exception:
        return Decimal('0')


def expense_category_code(expense: Dict[str, Any], tenant: Optional[TenantContext]) -> Optional[str]:
    node_id = expense.get('category_node_id')
    if not node_id:
        return None
    taxonomy = load_category_taxonomy_for_tenant(tenant)
    for node in taxonomy.values():
        if node.id == str(node_id):
            return node.code
    return None


def expense_guess_unchanged(expense: Dict[str, Any], tenant: Optional[TenantContext]) -> bool:
    guess_code = expense.get('category_guess_code')
    if not guess_code:
        return False
    current_code = expense_category_code(expense, tenant)
    if not current_code:
        return False
    guess_resolved = resolve_code(str(guess_code), tenant).code
    return guess_resolved == current_code


def lookup_memory(tenant: TenantContext, merchant_key: str) -> Optional[MemoryRow]:
    if not is_supabase_configured():
        return None
    try:
        client = get_supabase_client()
        response = (
            client.table('category_merchant_memory')
            .select('merchant_key, category_code, weight, display_merchant')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .eq('merchant_key', merchant_key)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        row = rows[0]
        return MemoryRow(
            merchant_key=str(row['merchant_key']),
            category_code=str(row['category_code']),
            weight=_decimal(row.get('weight')),
            display_merchant=row.get('display_merchant'),
        )
    except Exception:
        logger.exception('lookup_memory failed for %s', merchant_key)
        return None


def _upsert_memory(
    tenant: TenantContext,
    *,
    merchant_key: str,
    category_code: str,
    weight: Decimal,
    last_source: str,
    display_merchant: Optional[str] = None,
    sample_description: Optional[str] = None,
    last_corrected_by: Optional[str] = None,
) -> None:
    if not is_supabase_configured():
        return

    payload: Dict[str, Any] = {
        'tenant_type': tenant.tenant_type,
        'tenant_id': tenant.tenant_id,
        'merchant_key': merchant_key,
        'category_code': category_code,
        'weight': float(weight),
        'last_source': last_source,
        'updated_at': _now_iso(),
        'hit_count': 1,
    }
    if display_merchant:
        payload['display_merchant'] = display_merchant
    if sample_description:
        payload['sample_description'] = sample_description
    if last_corrected_by:
        payload['last_corrected_by'] = last_corrected_by

    try:
        client = get_supabase_client()
        existing = (
            client.table('category_merchant_memory')
            .select('id, weight, hit_count')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .eq('merchant_key', merchant_key)
            .limit(1)
            .execute()
        ).data or []

        if existing:
            row = existing[0]
            payload['hit_count'] = int(row.get('hit_count') or 0) + 1
            if last_source in (SOURCE_USER_CORRECTION, SOURCE_BACKFILL):
                payload['weight'] = float(weight)
            elif last_source in (SOURCE_LLM, SOURCE_SILENT_CONFIRM):
                payload['weight'] = float(_decimal(row.get('weight')) + weight)
            client.table('category_merchant_memory').update(payload).eq('id', row['id']).execute()
        else:
            client.table('category_merchant_memory').insert(payload).execute()
    except Exception:
        logger.exception('upsert memory failed for merchant_key=%s', merchant_key)


def upsert_llm_seed(
    tenant: TenantContext,
    *,
    merchant_key: str,
    category_code: str,
    display_merchant: Optional[str] = None,
    sample_description: Optional[str] = None,
) -> None:
    _upsert_memory(
        tenant,
        merchant_key=merchant_key,
        category_code=category_code,
        weight=WEIGHT_LLM_SEED,
        last_source=SOURCE_LLM,
        display_merchant=display_merchant,
        sample_description=sample_description,
    )


def record_user_correction(
    tenant: TenantContext,
    *,
    description: str,
    category_code: str,
    merchant_key: Optional[str] = None,
    display_merchant: Optional[str] = None,
    corrected_by: Optional[str] = None,
) -> None:
    key = merchant_key or heuristic_merchant_from_description(description)
    if not key:
        return
    _upsert_memory(
        tenant,
        merchant_key=key,
        category_code=category_code,
        weight=WEIGHT_USER_CORRECTION,
        last_source=SOURCE_USER_CORRECTION,
        display_merchant=display_merchant or description,
        sample_description=description,
        last_corrected_by=corrected_by,
    )


async def record_user_correction_from_description(
    tenant: TenantContext,
    *,
    description: str,
    category_code: str,
    gemini: GeminiClient,
    store_name: Optional[str] = None,
    corrected_by: Optional[str] = None,
) -> None:
    from services.merchant_resolve import resolve_raw_merchant

    item = {
        'description': description,
        'store_name': store_name,
        'amount': '',
        'currency': '',
    }
    raw, key = await resolve_raw_merchant(item, gemini)
    if not key:
        return
    record_user_correction(
        tenant,
        description=description,
        category_code=category_code,
        merchant_key=key,
        display_merchant=raw,
        corrected_by=corrected_by,
    )


def find_prior_expense_for_merchant(
    tenant: TenantContext,
    merchant_key: str,
    *,
    exclude_source_message_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not is_supabase_configured():
        return None
    try:
        client = get_supabase_client()
        query = (
            client.table('expenses')
            .select(
                'id, description, category_node_id, category_guess_code, '
                'source_message_id, created_at, metadata'
            )
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .is_('deleted_at', 'null')
            .order('created_at', desc=True)
            .limit(100)
        )
        if exclude_source_message_id:
            query = query.neq('source_message_id', exclude_source_message_id)
        rows = query.execute().data or []
        from services.merchant_resolve import merchant_key_from_expense_row

        for row in rows:
            key = merchant_key_from_expense_row(row)
            if key == merchant_key:
                return row
        return None
    except Exception:
        logger.exception('find_prior_expense_for_merchant failed')
        return None


def apply_silent_confirm(
    tenant: TenantContext,
    *,
    merchant_key: str,
    category_code: str,
    sample_description: Optional[str] = None,
    display_merchant: Optional[str] = None,
) -> None:
    _upsert_memory(
        tenant,
        merchant_key=merchant_key,
        category_code=category_code,
        weight=WEIGHT_SILENT_CONFIRM,
        last_source=SOURCE_SILENT_CONFIRM,
        display_merchant=display_merchant,
        sample_description=sample_description,
    )


def maybe_apply_silent_confirm_for_prior(
    tenant: TenantContext,
    *,
    merchant_key: str,
    category_code: str,
    display_merchant: Optional[str],
    sample_description: Optional[str],
    exclude_source_message_id: Optional[str] = None,
) -> None:
    prior = find_prior_expense_for_merchant(
        tenant,
        merchant_key,
        exclude_source_message_id=exclude_source_message_id,
    )
    if prior is None:
        return
    if not expense_guess_unchanged(prior, tenant):
        return
    apply_silent_confirm(
        tenant,
        merchant_key=merchant_key,
        category_code=category_code,
        sample_description=sample_description,
        display_merchant=display_merchant,
    )


def memory_category_is_valid(category_code: str, tenant: Optional[TenantContext]) -> bool:
    taxonomy = load_category_taxonomy_for_tenant(tenant)
    if category_code not in taxonomy:
        return False
    resolved = resolve_code(category_code, tenant)
    return resolved.code == category_code


def get_category_accuracy_stats(
    tenant: TenantContext,
    *,
    days: int = 30,
) -> Dict[str, Any]:
    if not is_supabase_configured():
        return {'total_expenses': 0, 'pct_guess_unchanged': 0.0, 'pct_guess_unknown': 0.0}
    try:
        client = get_supabase_client()
        response = client.rpc(
            'get_category_accuracy_stats',
            {
                'p_tenant_type': tenant.tenant_type,
                'p_tenant_id': tenant.tenant_id,
                'p_days': days,
            },
        ).execute()
        return response.data or {'total_expenses': 0, 'pct_guess_unchanged': 0.0, 'pct_guess_unknown': 0.0}
    except Exception:
        logger.exception('get_category_accuracy_stats failed')
        return {'total_expenses': 0, 'pct_guess_unchanged': 0.0, 'pct_guess_unknown': 0.0}
