# Quickstart: Wish List

**Feature**: 020-wish-list

## Prerequisites

- Features **009–015** baseline (dashboard auth, tenants, categories, expenses, budgets, budget pace)
- `GEMINI_API_KEY` for bot flows; `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` to persist
- Web: `web/.env.local` from `web/.env.example` with Supabase + LINE Login vars

## Apply migration

```bash
# From repo root — after adding supabase/migrations/*_wish_list_items.sql
supabase db push
# Or apply the migration SQL in the Supabase SQL editor
```

Verify:

```sql
\d wish_list_items
SELECT column_name FROM information_schema.columns
  WHERE table_name = 'expenses' AND column_name = 'wish_list_item_id';
```

## Run bot harness

```bash
python3 local_run.py --text "I want to buy headphones 15000 yen"
# Expect: no expense insert; budget impact + ask to add

# Confirm add (use bot_message_id from prior reply):
python3 local_run.py --reply-to <bot_message_id> --text "yes"

# Decline:
python3 local_run.py --reply-to <bot_message_id> --text "no"

# Ordinary expense must still work:
python3 local_run.py --text "Lunch 1200 yen"

# Image + wish text (combined path):
python3 local_run.py --image path/to/item.jpg --text "買いたい"
```

Group ledger:

```bash
python3 local_run.py --group-id <group_id> --text "買いたい コーヒーメーカー 8000円"
```

## Run web app

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000/wish-list` after LINE sign-in.

## Manual test flow

### 1. Web CRUD + priority

1. Open **Wish List** in the side drawer (personal ledger).
2. Add three items with different prices/categories; optional product link on one.
3. Reorder by drag/controls; reload — priority order persists.
4. Switch sort to **price** / **created** — order changes without destroying saved priority when returning to priority mode.
5. Edit one item; delete another; confirm validation on empty name / bad URL.

### 2. Execute → expense + tag

1. Execute an item; on confirm change amount and date; save.
2. Confirm item leaves active list; appears under **Executed** filter with **expense** values + link.
3. Open expenses list — card shows category **and** wish-list tag.
4. Log a normal expense — no wish-list tag.

### 3. Bot add + budget impact

1. Set a category or total budget on `/budget` with spending near the limit.
2. Bot: wish message that would put the bucket ahead of pace → remaining figures **and** pace note; reply `yes` → item on web active list.
3. Bot: wish message on/under pace → remaining only (no pace note).
4. Bot: wish with no budgets → unlimited / no budget messaging; still can add.
5. Reply `no` → nothing created.

### 4. Regression

1. `python3 -m pytest -q`
2. Spot-check normal text/image expense logging and reply-edit still work.

## Tests (automated)

```bash
python3 -m pytest -q
cd web && npm test && npm run lint
```
