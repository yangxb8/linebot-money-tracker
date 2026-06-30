# Quickstart: Budget Pace Alert in LINE Bot Replies

**Feature**: 015-budget-pace-alert

## Prerequisites

- Feature **012** (monthly budget manager) migrated and working in Supabase
- Feature **005** (reply-edit) working
- Python env: `pip install -r requirements.txt`
- `.env` with `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

## Setup budgets (web)

```bash
cd web && npm run dev
```

1. Sign in at `http://localhost:3000/budget`
2. Set an L2 budget for **外食** (e.g. ¥30,000) for the current month
3. Optionally set parent L1 and total budgets to test lowest-level warning logic

## Log expenses ahead of pace (bot)

```bash
# From repo root — pre-seed spending via repeated logs or Supabase SQL, then:
python3 local_run.py --text "ランチ 3000円"
```

**Expected** (when L2 外食 is ahead of pace after persist):

- Reply **starts** with emoji pace warning naming 外食 and daily ¥ allowance
- Blank line
- Standard confirmation (`検出した支出:` / `Detected expense(s):`)

**Expected** (on pace or no budget):

- Standard confirmation only — no pace block

## Test lowest-level warning cascade

1. Set L2 外食 ¥10k, L1 食費 ¥50k, total ¥100k
2. Log enough 外食 expenses so **all three** are ahead of pace
3. Confirm warning mentions **外食 (L2)** only — not L1 or total

4. Adjust data so L2 on pace but L1 ahead → warning mentions **L1** only

## Test reply-edit triggers

```bash
# Log expense, note bot_message_id from console output
python3 local_run.py --text "コーヒー 500円"
python3 local_run.py --reply-to <bot_message_id> --text "3000円"
```

When amount change pushes budget ahead of pace → edit summary is prepended with pace warning.

```bash
python3 local_run.py --reply-to <bot_message_id> --text "2"
```

Category pick via alternative number — if new category's lowest ahead level qualifies → pace warning prepended.

## Group ledger

```bash
python3 local_run.py --group-id <group_id> --text "チームランチ 5000円"
```

Pace figures must reflect **group** budgets, not personal.

## Run tests

```bash
python3 -m pytest tests/test_budget_pace.py -q
python3 -m pytest tests/test_message_handler_persistence.py tests/test_reply_edit.py -q
```

## Verify alignment with web

1. Open `/budget` for same tenant/month
2. Compare health tone on warned bucket — bot `is_ahead` should match web `paceRatio > 1`
3. Daily ¥ in warning should match `floor(remaining / daysLeft)` on budget row

## Troubleshooting

| Symptom | Check |
| ------- | ----- |
| No warning when expected | `has_any_limit` in RPC; expense `expense_date` fiscal month; Supabase keys set |
| Wrong level warned | L2/L1/total limits defined; lowest-ahead selection order |
| LLM failure still works | Template fallback in `budget_pace_i18n.py`; confirmation not blocked |
| `test_no_budget_impact_text` fails | Test updated to allow pace text when ahead of pace |
