# Quickstart: Monthly Expense Report

**Feature**: 022-monthly-expense-report

## Prerequisites

- Budgets + pace baseline (features **012**, **015**) and persona/reply-language settings (**016**, **019**)
- `GEMINI_API_KEY` for insight copy (template fallback still works if LLM fails)
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` to persist artifacts/tips and upload PNGs
- Migration applied for `monthly_report_artifacts`, `monthly_report_tips`, and Storage bucket `monthly-reports`

## Apply migration

```bash
# From repo root — migration file:
# supabase/migrations/20261127120000_monthly_report_artifacts.sql
supabase db push
# Or apply via Supabase MCP / SQL editor (tables + private bucket monthly-reports)
```

Applied on project `nyuenufldaqsjybjhawl` (tables `monthly_report_artifacts`, `monthly_report_tips`, bucket `monthly-reports`).

Verify:

```sql
SELECT to_regclass('public.monthly_report_artifacts');
SELECT to_regclass('public.monthly_report_tips');
SELECT id, public FROM storage.buckets WHERE id = 'monthly-reports';
```

## Seed a period worth reporting

Use the harness (or dashboard) to log several expenses in the **previous** fiscal period and set a total (+ optional category) budget for that period. Confirm **設定 → 会計月の開始日** if testing non-1 start days.

## Run bot harness

```bash
# Default = previous completed fiscal period
python3 local_run.py --text "monthly report"
# Expect: either image path printed (same-turn) or “preparing—ask again” text

# Ask again after prepare
python3 local_run.py --text "レポート見せて"

# Explicit current period
python3 local_run.py --text "this month's report"

# New-period tip: first message after fiscal rollover (any intent)
python3 local_run.py --text "Lunch 1200 yen"
# Expect: normal expense confirm PLUS tip that previous report is available on ask (once)

# Same conversation second message should not tip again
python3 local_run.py --text "Coffee 500 yen"

# Ordinary expense / wish must not be misclassified as report
python3 local_run.py --text "Lunch 1200 yen"
python3 local_run.py --text "I want to buy headphones 15000 yen"
```

Group ledger (tip once for the whole group conversation):

```bash
python3 local_run.py --group-id <group_id> --text "Hello"
python3 local_run.py --group-id <group_id> --user-id other-user --text "Hi"
# Second member should not get a second tip
python3 local_run.py --group-id <group_id> --text "monthly report"
```

## Automated tests

```bash
python3 -m pytest -q tests/test_monthly_report*.py tests/functional/bot/test_monthly_report_journey.py
python3 -m pytest -q   # full bot suite green
```

No new web/Playwright cases required for v1 (LINE-only surface).

## Manual acceptance checklist

- [ ] Unspecified ask → previous completed period (respects 会計月の開始日)
- [ ] Fast prepare → image same turn; slow → ask-again then image
- [ ] Primary graph is budget vs actual (total + worst-variance cats when budgeted)
- [ ] No budget → spending fallback + clear “no budget” copy
- [ ] Tip once per conversation after rollover; text only
- [ ] No expense/wish rows created by report asks
- [ ] Persona/language reflected on tip + on-image commentary
