-- Budget cascade verification (feature 012)
-- Run after seeding tenant expenses and monthly_budgets rows.

-- L2 budget hit: expense at L2 under budgeted category → spent_by_bucket['l2:<id>']
-- L1 fallback: no L2 budget, L1 budget exists → spent_by_bucket['l1:<id>']
-- Total only: only total budget row → spent_by_bucket['total']
-- Unbudgeted: no budgets → unbudgeted_spent = sum(expenses), spent_by_bucket empty
-- Soft-deleted: expense with deleted_at set → excluded from totals

-- Example RPC call:
-- SELECT get_budget_summary('user', '<line_user_id>', '2026-06-01', 'JPY');

-- Category change: update expense category_node_id / l1 / l2, re-run RPC;
-- old bucket decreases, new bucket increases.

-- Cross-month: change expense_date across months; both months' summaries update.

-- Mid-month first budget (FR-015): insert expenses before budget row;
-- get_budget_summary should include prior expenses in spent totals.
