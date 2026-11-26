"""Persistence + Storage for monthly report artifacts and tips."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from services.monthly_report_period import ReportPeriod
from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)

BUCKET = 'monthly-reports'
SIGNED_URL_TTL_SECONDS = 60 * 30

# In-memory fallback for local/tests without Supabase
_MEMORY_ARTIFACTS: Dict[str, Dict[str, Any]] = {}
_MEMORY_TIPS: set[tuple[str, str, str]] = set()
_MEMORY_BLOBS: Dict[str, bytes] = {}


def _artifact_key(tenant: TenantContext, period_start: date) -> str:
    return f'{tenant.tenant_type}:{tenant.tenant_id}:{period_start.isoformat()}'


@dataclass
class ArtifactRecord:
    id: str
    tenant_type: str
    tenant_id: str
    period_start: date
    period_end: date
    status: str
    data_fingerprint: str
    style_fingerprint: str
    storage_path: Optional[str]
    insight_text: Optional[str]
    snapshot_json: Optional[Dict[str, Any]]
    error_code: Optional[str]
    png_bytes: Optional[bytes] = None


def compute_data_fingerprint(tenant: TenantContext, period: ReportPeriod) -> str:
    payload: Dict[str, Any] = {
        'fiscal_start_day': period.fiscal_start_day,
        'period_start': period.period_start.isoformat(),
        'period_end': period.period_end.isoformat(),
        'expenses': [],
        'budgets': [],
    }
    if is_supabase_configured():
        try:
            client = get_supabase_client()
            expenses = (
                client.table('expenses')
                .select('id, amount, category_l1_id, category_l2_id, deleted_at')
                .eq('tenant_type', tenant.tenant_type)
                .eq('tenant_id', tenant.tenant_id)
                .gte('expense_date', period.period_start.isoformat())
                .lte('expense_date', period.period_end.isoformat())
                .execute()
            )
            payload['expenses'] = expenses.data or []
            budgets = (
                client.table('monthly_budgets')
                .select('budget_level, category_node_id, amount')
                .eq('tenant_type', tenant.tenant_type)
                .eq('tenant_id', tenant.tenant_id)
                .eq('budget_month', period.period_start.isoformat())
                .execute()
            )
            payload['budgets'] = budgets.data or []
        except Exception:
            logger.exception('fingerprint query failed')
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def compute_style_fingerprint(
    *,
    language: str,
    persona_preset: str,
    emoji_level: int,
    custom_text: str = '',
) -> str:
    raw = f'{language}|{persona_preset}|{emoji_level}|{custom_text}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def tip_already_shown(tenant: TenantContext, tip_period_start: date) -> bool:
    key = (tenant.tenant_type, tenant.tenant_id, tip_period_start.isoformat())
    if key in _MEMORY_TIPS:
        return True
    if not is_supabase_configured():
        return False
    try:
        client = get_supabase_client()
        response = (
            client.table('monthly_report_tips')
            .select('id')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .eq('tip_period_start', tip_period_start.isoformat())
            .maybe_single()
            .execute()
        )
        return bool(response.data)
    except Exception:
        logger.exception('tip_already_shown failed')
        return False


def mark_tip_shown(tenant: TenantContext, tip_period_start: date) -> None:
    key = (tenant.tenant_type, tenant.tenant_id, tip_period_start.isoformat())
    _MEMORY_TIPS.add(key)
    if not is_supabase_configured():
        return
    try:
        client = get_supabase_client()
        client.table('monthly_report_tips').upsert(
            {
                'tenant_type': tenant.tenant_type,
                'tenant_id': tenant.tenant_id,
                'tip_period_start': tip_period_start.isoformat(),
                'shown_at': datetime.now(timezone.utc).isoformat(),
            },
            on_conflict='tenant_type,tenant_id,tip_period_start',
        ).execute()
    except Exception:
        logger.exception('mark_tip_shown failed')


def get_artifact(tenant: TenantContext, period_start: date) -> Optional[ArtifactRecord]:
    mem_key = _artifact_key(tenant, period_start)
    if mem_key in _MEMORY_ARTIFACTS:
        return _row_to_record(_MEMORY_ARTIFACTS[mem_key], png=_MEMORY_BLOBS.get(mem_key))
    if not is_supabase_configured():
        return None
    try:
        client = get_supabase_client()
        response = (
            client.table('monthly_report_artifacts')
            .select('*')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .eq('period_start', period_start.isoformat())
            .maybe_single()
            .execute()
        )
        if not response.data:
            return None
        return _row_to_record(response.data)
    except Exception:
        logger.exception('get_artifact failed')
        return None


def upsert_preparing(
    tenant: TenantContext,
    period: ReportPeriod,
    *,
    data_fingerprint: str,
    style_fingerprint: str,
) -> ArtifactRecord:
    artifact_id = str(uuid.uuid4())
    existing = get_artifact(tenant, period.period_start)
    if existing:
        artifact_id = existing.id
    row = {
        'id': artifact_id,
        'tenant_type': tenant.tenant_type,
        'tenant_id': tenant.tenant_id,
        'period_start': period.period_start.isoformat(),
        'period_end': period.period_end.isoformat(),
        'status': 'preparing',
        'data_fingerprint': data_fingerprint,
        'style_fingerprint': style_fingerprint,
        'storage_path': None,
        'insight_text': None,
        'snapshot_json': None,
        'error_code': None,
        'prepared_at': None,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    mem_key = _artifact_key(tenant, period.period_start)
    _MEMORY_ARTIFACTS[mem_key] = row
    if is_supabase_configured():
        try:
            client = get_supabase_client()
            client.table('monthly_report_artifacts').upsert(
                row,
                on_conflict='tenant_type,tenant_id,period_start',
            ).execute()
        except Exception:
            logger.exception('upsert_preparing failed')
    return _row_to_record(row)


def mark_ready(
    tenant: TenantContext,
    period: ReportPeriod,
    *,
    artifact_id: str,
    data_fingerprint: str,
    style_fingerprint: str,
    insight_text: str,
    snapshot_json: Dict[str, Any],
    png_bytes: bytes,
) -> ArtifactRecord:
    storage_path = f'{tenant.tenant_type}/{tenant.tenant_id}/{period.period_start.isoformat()}/{artifact_id}.png'
    mem_key = _artifact_key(tenant, period.period_start)
    _MEMORY_BLOBS[mem_key] = png_bytes

    if is_supabase_configured():
        try:
            client = get_supabase_client()
            client.storage.from_(BUCKET).upload(
                storage_path,
                png_bytes,
                file_options={'content-type': 'image/png', 'upsert': 'true'},
            )
        except Exception:
            logger.exception('storage upload failed; keeping memory bytes only')
            storage_path = f'memory:{mem_key}'

    row = {
        'id': artifact_id,
        'tenant_type': tenant.tenant_type,
        'tenant_id': tenant.tenant_id,
        'period_start': period.period_start.isoformat(),
        'period_end': period.period_end.isoformat(),
        'status': 'ready',
        'data_fingerprint': data_fingerprint,
        'style_fingerprint': style_fingerprint,
        'storage_path': storage_path,
        'insight_text': insight_text,
        'snapshot_json': snapshot_json,
        'error_code': None,
        'prepared_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    _MEMORY_ARTIFACTS[mem_key] = row
    if is_supabase_configured() and not storage_path.startswith('memory:'):
        try:
            client = get_supabase_client()
            client.table('monthly_report_artifacts').upsert(
                row,
                on_conflict='tenant_type,tenant_id,period_start',
            ).execute()
        except Exception:
            logger.exception('mark_ready upsert failed')
    return _row_to_record(row, png=png_bytes)


def mark_failed(
    tenant: TenantContext,
    period: ReportPeriod,
    *,
    artifact_id: str,
    data_fingerprint: str,
    style_fingerprint: str,
    error_code: str,
) -> ArtifactRecord:
    row = {
        'id': artifact_id,
        'tenant_type': tenant.tenant_type,
        'tenant_id': tenant.tenant_id,
        'period_start': period.period_start.isoformat(),
        'period_end': period.period_end.isoformat(),
        'status': 'failed',
        'data_fingerprint': data_fingerprint,
        'style_fingerprint': style_fingerprint,
        'storage_path': None,
        'insight_text': None,
        'snapshot_json': None,
        'error_code': error_code,
        'prepared_at': None,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    mem_key = _artifact_key(tenant, period.period_start)
    _MEMORY_ARTIFACTS[mem_key] = row
    if is_supabase_configured():
        try:
            client = get_supabase_client()
            client.table('monthly_report_artifacts').upsert(
                row,
                on_conflict='tenant_type,tenant_id,period_start',
            ).execute()
        except Exception:
            logger.exception('mark_failed failed')
    return _row_to_record(row)


def signed_urls_for_artifact(artifact: ArtifactRecord) -> tuple[Optional[str], Optional[str], Optional[bytes]]:
    """Return (original_url, preview_url, png_bytes)."""
    mem_key = f'{artifact.tenant_type}:{artifact.tenant_id}:{artifact.period_start.isoformat()}'
    png = artifact.png_bytes or _MEMORY_BLOBS.get(mem_key)
    if artifact.storage_path and not artifact.storage_path.startswith('memory:') and is_supabase_configured():
        try:
            client = get_supabase_client()
            result = client.storage.from_(BUCKET).create_signed_url(
                artifact.storage_path,
                SIGNED_URL_TTL_SECONDS,
            )
            url = None
            if isinstance(result, dict):
                url = result.get('signedURL') or result.get('signedUrl')
            if url:
                return url, url, png
        except Exception:
            logger.exception('create_signed_url failed')
    return None, None, png


def _row_to_record(row: Dict[str, Any], png: Optional[bytes] = None) -> ArtifactRecord:
    period_start = row['period_start']
    period_end = row['period_end']
    if isinstance(period_start, str):
        period_start = date.fromisoformat(period_start[:10])
    if isinstance(period_end, str):
        period_end = date.fromisoformat(period_end[:10])
    snapshot = row.get('snapshot_json')
    if isinstance(snapshot, str):
        snapshot = json.loads(snapshot)
    return ArtifactRecord(
        id=str(row['id']),
        tenant_type=str(row['tenant_type']),
        tenant_id=str(row['tenant_id']),
        period_start=period_start,
        period_end=period_end,
        status=str(row['status']),
        data_fingerprint=str(row.get('data_fingerprint') or ''),
        style_fingerprint=str(row.get('style_fingerprint') or ''),
        storage_path=row.get('storage_path'),
        insight_text=row.get('insight_text'),
        snapshot_json=snapshot,
        error_code=row.get('error_code'),
        png_bytes=png,
    )


def clear_memory_store() -> None:
    """Test helper."""
    _MEMORY_ARTIFACTS.clear()
    _MEMORY_TIPS.clear()
    _MEMORY_BLOBS.clear()
