"""Hypothetical budget impact for wish-list add proposals (feature 020)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional

from services.budget_pace import (
    build_level_candidates,
    compute_budget_health,
    fetch_budget_summary,
    fetch_category_display_names,
    fiscal_period_start_for_date,
)
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WishBudgetImpact:
    has_budget: bool
    level: Optional[str]
    label: Optional[str]
    limit: Optional[float]
    spent_now: Optional[float]
    remaining_now: Optional[float]
    remaining_if_purchased: Optional[float]
    is_ahead_if_purchased: bool
    days_remaining: Optional[int]
    daily_allowance_if_purchased: Optional[float]


def build_wish_list_budget_impact(
    tenant: TenantContext,
    amount: float,
    *,
    assigned_level: int,
    category_node_id: str,
    category_l1_id: str,
    currency: str = 'JPY',
    as_of_date: Optional[date] = None,
) -> WishBudgetImpact:
    """Compute remaining now / if purchased and whether pace would be ahead."""
    empty = WishBudgetImpact(
        has_budget=False,
        level=None,
        label=None,
        limit=None,
        spent_now=None,
        remaining_now=None,
        remaining_if_purchased=None,
        is_ahead_if_purchased=False,
        days_remaining=None,
        daily_allowance_if_purchased=None,
    )
    try:
        today = as_of_date or date.today()
        # Prefer RPC fiscal metadata; bootstrap month from calendar day.
        budget_month = date(today.year, today.month, 1)
        summary = fetch_budget_summary(tenant, budget_month, currency=currency)
        if not summary or not summary.get('has_any_limit'):
            return empty

        # Align budget_month with fiscal period when RPC returns it.
        if summary.get('budget_month'):
            try:
                budget_month = date.fromisoformat(str(summary['budget_month'])[:10])
            except ValueError:
                pass

        # If caller date falls in a different fiscal month, refetch.
        fiscal_start = int(summary.get('fiscal_start_day') or 1)
        expected_start = fiscal_period_start_for_date(today, fiscal_start)
        if expected_start != budget_month:
            summary = fetch_budget_summary(tenant, expected_start, currency=currency)
            if not summary or not summary.get('has_any_limit'):
                return empty
            budget_month = expected_start

        budgets = summary.get('budgets') or []
        spent_by_bucket = summary.get('spent_by_bucket') or {}
        elapsed_days = int(summary.get('elapsed_days') or 1)
        days_in_month = int(summary.get('days_in_month') or 30)

        expense_row: Dict[str, Any] = {
            'assigned_level': assigned_level,
            'category_node_id': category_node_id,
            'category_l1_id': category_l1_id,
        }
        names = fetch_category_display_names(
            tenant,
            [category_node_id, category_l1_id],
        )
        candidates = build_level_candidates(
            expense_row,
            budgets,
            spent_by_bucket,
            names,
            'ja',
        )
        if not candidates:
            return empty

        # Lowest (most specific) candidate first — same order as build_level_candidates.
        candidate = candidates[0]
        spent_now = float(candidate.spent)
        limit = float(candidate.limit)
        remaining_now = max(limit - spent_now, 0.0)
        spent_if = spent_now + float(amount)
        remaining_if = max(limit - spent_if, 0.0)
        health_if = compute_budget_health(spent_if, limit, elapsed_days, days_in_month)
        days_remaining = max(days_in_month - elapsed_days, 0)
        daily = (
            float(Decimal(str(remaining_if)) // days_remaining)
            if days_remaining > 0
            else 0.0
        )

        return WishBudgetImpact(
            has_budget=True,
            level=candidate.level,
            label=candidate.display_name,
            limit=limit,
            spent_now=spent_now,
            remaining_now=remaining_now,
            remaining_if_purchased=remaining_if,
            is_ahead_if_purchased=health_if.is_ahead,
            days_remaining=days_remaining,
            daily_allowance_if_purchased=daily,
        )
    except Exception:
        logger.exception('build_wish_list_budget_impact failed; fail-open')
        return empty
