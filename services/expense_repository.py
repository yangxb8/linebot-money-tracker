from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from services.category_taxonomy import CategoryNode, load_category_taxonomy_for_tenant, resolve_code
from services.message_context import MessageContext
from services.tenant_context import TenantContext
from services.tenant_context import TenantContext
from services.supabase_client import get_supabase_client, is_supabase_configured

logger = logging.getLogger(__name__)

JST = ZoneInfo('Asia/Tokyo')


@dataclass
class ExpenseInsertRow:
    tenant_type: str
    tenant_id: str
    logged_by_line_user_id: str
    line_user_id: str
    source_message_id: str
    line_item_index: int
    description: str
    amount: Decimal
    currency: str
    expense_date: date
    category_node_id: str
    assigned_level: int
    category_l1_id: str
    category_l2_id: Optional[str]
    category_l3_id: Optional[str]
    category_guess_code: Optional[str] = None
    category_source: Optional[str] = None


@dataclass
class PersistResult:
    inserted: int
    skipped: int
    error: Optional[str] = None


@dataclass
class UpdateResult:
    success: bool
    error: Optional[str] = None


@dataclass
class MutationResult:
    success: bool
    affected: int = 0
    error: Optional[str] = None


@dataclass
class ExpenseRow:
    id: str
    line_user_id: str
    description: str
    amount: Decimal
    currency: str
    expense_date: date
    category_node_id: str
    assigned_level: int
    category_l1_id: str
    category_l2_id: Optional[str]
    category_l3_id: Optional[str]
    deleted_at: Optional[str] = None


def load_category_taxonomy_from_repo(tenant: Optional[TenantContext] = None):
    """Re-export for expense-persistence contract."""
    return load_category_taxonomy_for_tenant(tenant)


def expense_date_for_item(item: Dict[str, Any]) -> date:
    raw = item.get('expense_date')
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return date.fromisoformat(raw.strip()[:10])
        except ValueError:
            logger.warning('Invalid expense_date %r; using JST today', raw)
    return datetime.now(JST).date()


def build_insert_row(
    *,
    context: MessageContext,
    item: Dict[str, Any],
    line_item_index: int,
    category_code: str,
    category_guess_code: Optional[str] = None,
    category_source: Optional[str] = None,
) -> ExpenseInsertRow:
    node = resolve_code(category_code, context.tenant)
    amount_raw = item.get('amount', 0)
    amount = Decimal(str(amount_raw)).quantize(Decimal('0.01'))
    currency = str(item.get('currency') or 'JPY').strip().upper()[:3] or 'JPY'
    description = str(item.get('description', 'Expense')).strip() or 'Expense'

    tenant = context.tenant
    return ExpenseInsertRow(
        tenant_type=tenant.tenant_type,
        tenant_id=tenant.tenant_id,
        logged_by_line_user_id=tenant.logged_by_line_user_id,
        line_user_id=tenant.logged_by_line_user_id,
        source_message_id=context.source_message_id,
        line_item_index=line_item_index,
        description=description,
        amount=amount,
        currency=currency,
        expense_date=expense_date_for_item(item),
        category_node_id=node.id,
        assigned_level=node.level,
        category_l1_id=node.l1_id,
        category_l2_id=node.l2_id,
        category_l3_id=node.l3_id,
        category_guess_code=category_guess_code or category_code,
        category_source=category_source,
    )


def _row_to_dict(row: ExpenseInsertRow) -> Dict[str, Any]:
    data = asdict(row)
    data['amount'] = float(row.amount)
    data['expense_date'] = row.expense_date.isoformat()
    return data


def insert_expenses(rows: List[ExpenseInsertRow]) -> PersistResult:
    if not rows:
        return PersistResult(inserted=0, skipped=0)

    if not is_supabase_configured():
        logger.warning(
            'Supabase not configured; skipping persistence of %d expense row(s)',
            len(rows),
        )
        return PersistResult(inserted=0, skipped=0)

    try:
        client = get_supabase_client()
        payload = [_row_to_dict(row) for row in rows]
        before_count = _count_existing_rows(client, rows)

        response = (
            client.table('expenses')
            .upsert(
                payload,
                on_conflict='tenant_type,tenant_id,source_message_id,line_item_index',
                ignore_duplicates=True,
            )
            .execute()
        )

        returned = len(response.data or [])
        inserted = max(returned, 0)
        if returned == 0 and before_count is not None:
            after_count = _count_existing_rows(client, rows)
            if after_count is not None:
                inserted = max(after_count - before_count, 0)

        skipped = len(rows) - inserted
        logger.info(
            'Persisted expenses: inserted=%d skipped=%d total=%d',
            inserted,
            skipped,
            len(rows),
        )
        return PersistResult(inserted=inserted, skipped=skipped)
    except Exception as exc:
        logger.exception('insert_expenses failed')
        return PersistResult(inserted=0, skipped=0, error=str(exc))


def _count_existing_rows(client, rows: List[ExpenseInsertRow]) -> Optional[int]:
    if not rows:
        return 0
    try:
        sample = rows[0]
        response = (
            client.table('expenses')
            .select('id', count='exact')
            .eq('tenant_type', sample.tenant_type)
            .eq('tenant_id', sample.tenant_id)
            .eq('source_message_id', sample.source_message_id)
            .execute()
        )
        return response.count or 0
    except Exception:
        return None


def monthly_expense_total(
    tenant: TenantContext,
    year: int,
    month: int,
    category_node_id: str,
    currency: str,
) -> Decimal:
    if not is_supabase_configured():
        logger.warning('Supabase not configured; monthly_expense_total returns 0')
        return Decimal('0')

    try:
        client = get_supabase_client()
        response = client.rpc(
            'monthly_expense_total',
            {
                'p_tenant_type': tenant.tenant_type,
                'p_tenant_id': tenant.tenant_id,
                'p_year': year,
                'p_month': month,
                'p_category_node_id': category_node_id,
                'p_currency': currency.upper()[:3],
            },
        ).execute()
        value = response.data
        if value is None:
            return Decimal('0')
        return Decimal(str(value))
    except Exception:
        logger.exception('monthly_expense_total RPC failed')
        return Decimal('0')


def yearly_expense_total(
    tenant: TenantContext,
    year: int,
    category_node_id: str,
    currency: str,
) -> Decimal:
    if not is_supabase_configured():
        logger.warning('Supabase not configured; yearly_expense_total returns 0')
        return Decimal('0')

    try:
        client = get_supabase_client()
        response = client.rpc(
            'yearly_expense_total',
            {
                'p_tenant_type': tenant.tenant_type,
                'p_tenant_id': tenant.tenant_id,
                'p_year': year,
                'p_category_node_id': category_node_id,
                'p_currency': currency.upper()[:3],
            },
        ).execute()
        value = response.data
        if value is None:
            return Decimal('0')
        return Decimal(str(value))
    except Exception:
        logger.exception('yearly_expense_total RPC failed')
        return Decimal('0')


def fetch_expense_ids_for_message(
    tenant: TenantContext,
    source_message_id: str,
) -> List[Dict[str, Any]]:
    """Return expense id and line_item_index rows for a source message."""
    if not is_supabase_configured():
        return []

    try:
        client = get_supabase_client()
        response = (
            client.table('expenses')
            .select('id, line_item_index')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .eq('source_message_id', source_message_id)
            .order('line_item_index')
            .execute()
        )
        return response.data or []
    except Exception:
        logger.exception('fetch_expense_ids_for_message failed')
        return []


def _row_from_db(raw: Dict[str, Any]) -> ExpenseRow:
    amount = Decimal(str(raw.get('amount', 0))).quantize(Decimal('0.01'))
    expense_date_raw = raw.get('expense_date')
    if isinstance(expense_date_raw, str):
        expense_date = date.fromisoformat(expense_date_raw[:10])
    elif isinstance(expense_date_raw, date):
        expense_date = expense_date_raw
    else:
        expense_date = datetime.now(JST).date()

    return ExpenseRow(
        id=str(raw['id']),
        line_user_id=str(raw.get('line_user_id', '')),
        description=str(raw.get('description', '')),
        amount=amount,
        currency=str(raw.get('currency', 'JPY')),
        expense_date=expense_date,
        category_node_id=str(raw.get('category_node_id', '')),
        assigned_level=int(raw.get('assigned_level', 1)),
        category_l1_id=str(raw.get('category_l1_id', '')),
        category_l2_id=raw.get('category_l2_id'),
        category_l3_id=raw.get('category_l3_id'),
        deleted_at=raw.get('deleted_at'),
    )


def get_expenses_by_ids(expense_ids: List[str]) -> List[ExpenseRow]:
    if not expense_ids or not is_supabase_configured():
        return []

    try:
        client = get_supabase_client()
        response = (
            client.table('expenses')
            .select('*')
            .in_('id', expense_ids)
            .execute()
        )
        return [_row_from_db(row) for row in (response.data or [])]
    except Exception:
        logger.exception('get_expenses_by_ids failed')
        return []


def update_expense_fields(
    expense_id: str,
    *,
    description: Optional[str] = None,
    amount: Optional[Decimal] = None,
    currency: Optional[str] = None,
    expense_date: Optional[date] = None,
    category_code: Optional[str] = None,
    tenant: Optional[TenantContext] = None,
) -> UpdateResult:
    if not is_supabase_configured():
        return UpdateResult(success=False, error='Supabase not configured')

    payload: Dict[str, Any] = {'updated_at': datetime.now(JST).isoformat()}
    if description is not None:
        payload['description'] = description.strip() or 'Expense'
    if amount is not None:
        payload['amount'] = float(amount.quantize(Decimal('0.01')))
    if currency is not None:
        payload['currency'] = currency.strip().upper()[:3]
    if expense_date is not None:
        payload['expense_date'] = expense_date.isoformat()
    if category_code is not None:
        node = resolve_code(category_code, tenant)
        payload['category_node_id'] = node.id
        payload['assigned_level'] = node.level
        payload['category_l1_id'] = node.l1_id
        payload['category_l2_id'] = node.l2_id
        payload['category_l3_id'] = node.l3_id

    if len(payload) == 1:
        return UpdateResult(success=True)

    try:
        client = get_supabase_client()
        client.table('expenses').update(payload).eq('id', expense_id).execute()
        return UpdateResult(success=True)
    except Exception as exc:
        logger.exception('update_expense_fields failed')
        return UpdateResult(success=False, error=str(exc))


def soft_delete_expenses(expense_ids: List[str]) -> MutationResult:
    if not expense_ids:
        return MutationResult(success=True, affected=0)
    if not is_supabase_configured():
        return MutationResult(success=False, error='Supabase not configured')

    now = datetime.now(JST).isoformat()
    try:
        client = get_supabase_client()
        response = (
            client.table('expenses')
            .update({'deleted_at': now, 'updated_at': now})
            .in_('id', expense_ids)
            .is_('deleted_at', 'null')
            .execute()
        )
        affected = len(response.data or [])
        return MutationResult(success=True, affected=affected)
    except Exception as exc:
        logger.exception('soft_delete_expenses failed')
        return MutationResult(success=False, error=str(exc))


def restore_expenses(expense_ids: List[str]) -> MutationResult:
    if not expense_ids:
        return MutationResult(success=True, affected=0)
    if not is_supabase_configured():
        return MutationResult(success=False, error='Supabase not configured')

    now = datetime.now(JST).isoformat()
    try:
        client = get_supabase_client()
        response = (
            client.table('expenses')
            .update({'deleted_at': None, 'updated_at': now})
            .in_('id', expense_ids)
            .not_.is_('deleted_at', 'null')
            .execute()
        )
        affected = len(response.data or [])
        return MutationResult(success=True, affected=affected)
    except Exception as exc:
        logger.exception('restore_expenses failed')
        return MutationResult(success=False, error=str(exc))
