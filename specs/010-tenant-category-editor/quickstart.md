# Quickstart: Tenant Category Editor

**Feature**: 010-tenant-category-editor

## Prerequisites

- Feature **009** web dashboard running locally (`cd web && npm run dev`)
- Supabase env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, anon key in web `.env.local`
- At least one personal expense logged via bot (to test remap on init)

## Apply migration

```bash
# From repo root — apply via Supabase CLI or dashboard SQL
supabase db push
# Or run supabase/migrations/20260620140000_tenant_category_nodes.sql manually
```

## Local web workflow

```bash
cd web && npm install && npm run dev
```

1. Sign in at `http://localhost:3000/login`
2. Open the side drawer (☰) and tap **Categories**
3. Confirm default taxonomy appears (lazy copy on first visit)
4. Add L2 under 食費, rename an L1, reorder siblings
5. Open drawer → **Expenses** — existing expenses show updated names after remap

## Delete with transfer

1. Log expense via bot: `python local_run.py --text "ランチ 1000円"`
2. Open Categories, delete the assigned L2
3. Pick another L1 or L2 as transfer target
4. Refresh Expenses — row shows new category

## Group taxonomy

```bash
python local_run.py --group-id <group_id> --text "会議弁当 500円"
```

1. Sign in as a member; select group in tenant switcher
2. Open Categories — edit shared tree
3. Second member (or same user) logs expense in group — bot uses updated taxonomy

## Bot verification

```bash
# After customizing personal taxonomy on web
python local_run.py --text "スーパー 2500円"
```

Confirmation should list category options from tenant taxonomy only (including custom L2 names).

## Tests

```bash
pytest tests/test_tenant_category_taxonomy.py tests/test_category_delete_transfer.py -v
cd web && npm test   # when API route tests added
```

## RLS smoke query (service role impersonation)

Documented in `contracts/supabase-schema-delta.md` — verify cross-tenant write returns policy violation.
