# Contract: Environment Variables (004 extension)

**Feature**: 004-supabase-expense-storage  
**Extends**: `specs/003-local-dev-setup/contracts/environment-variables.md`

## New variables

| Variable | Required (webhook) | Required (console) | Secret | Description |
| -------- | ------------------ | ------------------ | ------ | ----------- |
| `SUPABASE_URL` | yes* | no | no | Project URL e.g. `https://nyuenufldaqsjybjhawl.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | yes* | no | **yes** | Server-side insert key; never expose to client |
| `LOCAL_LINE_USER_ID` | no | no | no | Console stand-in user id (default `local-dev-user`) |

\*Required when expense persistence is enabled. Webhook startup SHOULD fail fast if persistence is mandatory for deployment; console MAY omit for GEMINI-only testing.

## Example `.env` block

```env
# Supabase (expense persistence)
SUPABASE_URL=https://nyuenufldaqsjybjhawl.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Optional — console harness stand-in
# LOCAL_LINE_USER_ID=local-dev-user
```

## Security

- **Never** commit service role key
- **Never** use anon/publishable key for inserts (no RLS policies for end users in v1)
- Rotate key if leaked via Supabase dashboard

## Cloud Run

Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` as secrets/env vars alongside existing LINE + Gemini vars.

## Obtaining credentials

1. Open [Supabase Dashboard](https://supabase.com/dashboard) → project `nyuenufldaqsjybjhawl`
2. Settings → API → Project URL + `service_role` key (secret)
