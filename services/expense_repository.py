from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from services.category_taxonomy import CategoryNode, load_category_taxonomy, resolve_code
from services.message_context import MessageContext
from services.supabase_client import get_supabase_client, is_supabase_configured

logger = logging.getLogger(__name__)

JST = ZoneInfo('Asia/Tokyo')


@dataclass
class ExpenseInsertRow:
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


@dataclass
class PersistResult:
    inserted: int
    skipped: int
    error: Optional[str] = None


def load_category_taxonomy_from_repo():
    """Re-export for expense-persistence contract."""
    return load_category_taxonomy()


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
) -> ExpenseInsertRow:
    node = resolve_code(category_code)
    amount_raw = item.get('amount', 0)
    amount = Decimal(str(amount_raw)).quantize(Decimal('0.01'))
    currency = str(item.get('currency', 'JPY')).strip().upper()[:3]
    description = str(item.get('description', 'Expense')).strip() or 'Expense'

    return ExpenseInsertRow(
        line_user_id=context.line_user_id,
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
                on_conflict='line_user_id,source_message_id,line_item_index',
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
            .eq('line_user_id', sample.line_user_id)
            .eq('source_message_id', sample.source_message_id)
            .execute()
        )
        return response.count or 0
    except Exception:
        return None


def monthly_expense_total(
    line_user_id: str,
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
                'p_line_user_id': line_user_id,
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
    line_user_id: str,
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
                'p_line_user_id': line_user_id,
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
