# Supabase Schema Delta: Monthly Report

**Feature**: 022-monthly-expense-report

## Migration (new)

`supabase/migrations/YYYYMMDDHHMMSS_monthly_report_artifacts.sql`

### Tables

1. `public.monthly_report_artifacts` — see [data-model.md](../data-model.md)
2. `public.monthly_report_tips` — see data-model.md

### RLS

- Enable RLS on both tables.
- **No** anon/authenticated policies required for v1 (bot uses **service role** only, same pattern as confirmations / backend-only tables).
- Optionally revoke grants from `anon` / `authenticated` explicitly for defense in depth.

### Storage

Create private bucket:

```text
bucket_id: monthly-reports
public: false
```

Policies: allow **service_role** full access only. No public read.

Object key convention:

```text
{tenant_type}/{tenant_id}/{period_start}/{artifact_id}.png
```

### RPCs

None required for v1. Reads use existing `get_budget_summary` (or equivalent repository queries already used by `budget_pace.py`).

## App env

No new public env vars. Bot already has `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`. Signed URL generation uses the service-role client.

LINE delivery requires the signed URL host to be reachable by LINE’s servers (Supabase Storage default host is fine if project allows egress/fetch).
