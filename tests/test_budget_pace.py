"""Tests for budget pace evaluation and reply prepending."""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from services.budget_pace import (
    BudgetLevelCandidate,
    build_level_candidates,
    compute_budget_health,
    evaluate_pace_warnings,
    expense_rows_from_enriched,
    find_lowest_ahead_warning,
    fiscal_period_start_for_date,
    maybe_prepend_budget_pace_warning,
)
from services.message_context import MessageContext
from services.tenant_context import TenantContext


class TestComputeBudgetHealth(unittest.TestCase):
    def test_neutral_when_no_limit(self):
        health = compute_budget_health(5000, None, 10, 30)
        self.assertFalse(health.is_ahead)
        self.assertIsNone(health.pace_ratio)

    def test_neutral_on_day_1(self):
        health = compute_budget_health(5000, 50000, 1, 30)
        self.assertFalse(health.is_ahead)
        self.assertIsNone(health.pace_ratio)

    def test_good_when_under_pace(self):
        health = compute_budget_health(10000, 50000, 15, 30)
        self.assertFalse(health.is_ahead)

    def test_bad_when_far_over_pace(self):
        health = compute_budget_health(35000, 50000, 7, 30)
        self.assertTrue(health.is_ahead)

    def test_handles_over_100_percent_spent(self):
        health = compute_budget_health(60000, 50000, 20, 30)
        self.assertTrue(health.is_ahead)


class TestLowestAheadSelection(unittest.TestCase):
    def _candidate(self, level, node_id, limit, spent, name):
        return BudgetLevelCandidate(
            level=level,
            category_node_id=node_id,
            limit=Decimal(limit),
            spent=Decimal(spent),
            display_name=name,
        )

    def test_warns_l2_when_all_levels_ahead(self):
        candidates = [
            self._candidate('l2', 'l2-id', 10000, 9000, '外食'),
            self._candidate('l1', 'l1-id', 50000, 45000, '食費'),
            self._candidate('total', None, 100000, 90000, '総予算'),
        ]
        warning = find_lowest_ahead_warning(candidates, elapsed_days=10, days_in_month=30, language='ja')
        self.assertIsNotNone(warning)
        self.assertEqual(warning.level, 'l2')

    def test_warns_l1_when_l2_on_pace(self):
        candidates = [
            self._candidate('l2', 'l2-id', 10000, 2000, '外食'),
            self._candidate('l1', 'l1-id', 50000, 45000, '食費'),
        ]
        warning = find_lowest_ahead_warning(candidates, elapsed_days=10, days_in_month=30, language='ja')
        self.assertIsNotNone(warning)
        self.assertEqual(warning.level, 'l1')

    def test_no_warning_when_on_pace(self):
        candidates = [self._candidate('l2', 'l2-id', 50000, 10000, '外食')]
        warning = find_lowest_ahead_warning(candidates, elapsed_days=15, days_in_month=30, language='ja')
        self.assertIsNone(warning)


class TestBuildLevelCandidates(unittest.TestCase):
    def test_skips_undefined_levels(self):
        budgets = [
            {'budget_level': 'l2', 'category_node_id': 'l2-id', 'amount': 10000},
            {'budget_level': 'total', 'category_node_id': None, 'amount': 100000},
        ]
        expense = {
            'assigned_level': 2,
            'category_node_id': 'l2-id',
            'category_l1_id': 'l1-id',
        }
        candidates = build_level_candidates(
            expense,
            budgets,
            {'l2:l2-id': 5000, 'total': 20000},
            {'l2-id': '外食'},
            'ja',
        )
        levels = [c.level for c in candidates]
        self.assertEqual(levels, ['l2', 'total'])


class TestFiscalPeriodStart(unittest.TestCase):
    def test_calendar_month(self):
        self.assertEqual(
            fiscal_period_start_for_date(date(2026, 6, 15), 1),
            date(2026, 6, 1),
        )

    def test_custom_fiscal_start(self):
        self.assertEqual(
            fiscal_period_start_for_date(date(2026, 6, 10), 25),
            date(2026, 5, 25),
        )


class TestMaybePrependBudgetPaceWarning(unittest.IsolatedAsyncioTestCase):
    async def test_prepends_when_ahead(self):
        warning = find_lowest_ahead_warning(
            [
                BudgetLevelCandidate('l2', 'l2-id', Decimal(10000), Decimal(9000), '外食'),
            ],
            elapsed_days=10,
            days_in_month=30,
            language='ja',
        )
        with patch('services.budget_pace.evaluate_pace_warnings', return_value=[warning]):
            result = await maybe_prepend_budget_pace_warning(
                '検出した支出:',
                expense_rows=[{'assigned_level': 2}],
                tenant=TenantContext.personal('u1'),
                language='ja',
            )
        self.assertTrue(result.startswith('⚠️'))
        self.assertIn('\n\n検出した支出:', result)

    async def test_unchanged_when_no_warnings(self):
        with patch('services.budget_pace.evaluate_pace_warnings', return_value=[]):
            result = await maybe_prepend_budget_pace_warning(
                '検出した支出:',
                expense_rows=[{'assigned_level': 2}],
                tenant=TenantContext.personal('u1'),
                language='ja',
            )
        self.assertEqual(result, '検出した支出:')

    async def test_llm_fallback_on_failure(self):
        warning = find_lowest_ahead_warning(
            [
                BudgetLevelCandidate('l2', 'l2-id', Decimal(10000), Decimal(9000), '外食'),
            ],
            elapsed_days=10,
            days_in_month=30,
            language='ja',
        )
        gemini = MagicMock()
        gemini.generate_reply = AsyncMock(side_effect=RuntimeError('llm down'))
        with patch('services.budget_pace.evaluate_pace_warnings', return_value=[warning]):
            result = await maybe_prepend_budget_pace_warning(
                'Body',
                expense_rows=[{'assigned_level': 2}],
                tenant=TenantContext.personal('u1'),
                language='ja',
                gemini=gemini,
            )
        self.assertIn('⚠️', result)
        self.assertIn('Body', result)

    async def test_returns_body_on_evaluation_error(self):
        with patch('services.budget_pace.evaluate_pace_warnings', side_effect=RuntimeError('rpc fail')):
            result = await maybe_prepend_budget_pace_warning(
                'Body',
                expense_rows=[{'assigned_level': 2}],
                tenant=TenantContext.personal('u1'),
                language='ja',
            )
        self.assertEqual(result, 'Body')


class TestEvaluatePaceWarnings(unittest.TestCase):
    @patch('services.budget_pace.fetch_budget_summary')
    @patch('services.budget_pace.fetch_category_display_names', return_value={'l2-id': '外食'})
    def test_evaluates_with_mock_summary(self, _names, fetch_summary):
        fetch_summary.return_value = {
            'has_any_limit': True,
            'elapsed_days': 10,
            'days_in_month': 30,
            'budgets': [{'budget_level': 'l2', 'category_node_id': 'l2-id', 'amount': 10000}],
            'spent_by_bucket': {'l2:l2-id': 9000},
        }
        rows = [
            {
                'assigned_level': 2,
                'category_node_id': 'l2-id',
                'category_l1_id': 'l1-id',
                'expense_date': date(2026, 6, 15),
                'currency': 'JPY',
            }
        ]
        warnings = evaluate_pace_warnings(rows, TenantContext.personal('u1'), language='ja')
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].level, 'l2')

    @patch('services.budget_pace.fetch_budget_summary')
    @patch(
        'services.budget_pace.fetch_category_display_names',
        return_value={'l2-a': '外食', 'l2-b': '超市', 'l1-id': '食費'},
    )
    def test_dedupes_same_l1_bucket_across_multiple_l2_paths(self, _names, fetch_summary):
        fetch_summary.return_value = {
            'has_any_limit': True,
            'elapsed_days': 10,
            'days_in_month': 30,
            'budgets': [{'budget_level': 'l1', 'category_node_id': 'l1-id', 'amount': 50000}],
            'spent_by_bucket': {'l1:l1-id': 45000},
        }
        rows = [
            {
                'assigned_level': 2,
                'category_node_id': 'l2-a',
                'category_l1_id': 'l1-id',
                'expense_date': date(2026, 6, 15),
                'currency': 'JPY',
            },
            {
                'assigned_level': 2,
                'category_node_id': 'l2-b',
                'category_l1_id': 'l1-id',
                'expense_date': date(2026, 6, 15),
                'currency': 'JPY',
            },
        ]
        warnings = evaluate_pace_warnings(rows, TenantContext.personal('u1'), language='ja')
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].level, 'l1')
        self.assertEqual(warnings[0].category_node_id, 'l1-id')

    @patch('services.budget_pace.fetch_budget_summary')
    @patch(
        'services.budget_pace.fetch_category_display_names',
        return_value={'l2-a': '外食', 'l2-b': '交通', 'l1-a': '食費', 'l1-b': '交通費'},
    )
    def test_keeps_distinct_l1_buckets(self, _names, fetch_summary):
        fetch_summary.return_value = {
            'has_any_limit': True,
            'elapsed_days': 10,
            'days_in_month': 30,
            'budgets': [
                {'budget_level': 'l1', 'category_node_id': 'l1-a', 'amount': 50000},
                {'budget_level': 'l1', 'category_node_id': 'l1-b', 'amount': 20000},
            ],
            'spent_by_bucket': {'l1:l1-a': 45000, 'l1:l1-b': 18000},
        }
        rows = [
            {
                'assigned_level': 2,
                'category_node_id': 'l2-a',
                'category_l1_id': 'l1-a',
                'expense_date': date(2026, 6, 15),
                'currency': 'JPY',
            },
            {
                'assigned_level': 2,
                'category_node_id': 'l2-b',
                'category_l1_id': 'l1-b',
                'expense_date': date(2026, 6, 15),
                'currency': 'JPY',
            },
        ]
        warnings = evaluate_pace_warnings(rows, TenantContext.personal('u1'), language='ja')
        self.assertEqual(len(warnings), 2)
        self.assertEqual({w.category_node_id for w in warnings}, {'l1-a', 'l1-b'})


class TestExpenseRowsFromEnriched(unittest.TestCase):
    def test_builds_rows_from_enriched_items(self):
        context = MessageContext(
            tenant=TenantContext.personal('u1'),
            source_message_id='msg-1',
            reply_language='ja',
        )
        rows = expense_rows_from_enriched(
            [
                {
                    'description': 'Lunch',
                    'amount': 1200,
                    'currency': 'JPY',
                    'category_guess_code': 'unknown',
                }
            ],
            context,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['assigned_level'], 1)


if __name__ == '__main__':
    unittest.main()
