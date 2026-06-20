# Contract: Environment Variables

**Feature**: 009-expense-web-dashboard

## Web app (`web/.env.local` / Vercel)

| Variable | Required | Exposure | Description |
| -------- | -------- | -------- | ----------- |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Public | `https://nyuenufldaqsjybjhawl.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Public | Supabase publishable/anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | **Server only** | Admin user upsert in auth routes |
| `LINE_CHANNEL_ID` | Yes | Server (+ public client_id in OAuth URL) | Same channel as bot |
| `LINE_CHANNEL_SECRET` | Yes | **Server only** | OAuth code exchange |
| `NEXT_PUBLIC_LINE_LIFF_ID` | Yes | Public | LIFF app ID |
| `NEXT_PUBLIC_APP_URL` | Yes | Public | `https://<app>.vercel.app` or `http://localhost:3000` |

### Optional

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `EXPENSE_PAGE_SIZE` | `20` | Pagination size |

## Bot / rich menu script (existing + new)

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `LINE_CHANNEL_ACCESS_TOKEN` | Yes | Rich menu create/link API |
| `DASHBOARD_LIFF_URL` | Yes | `https://liff.line.me/{LIFF_ID}` for menu action |

## Unchanged bot variables

`LINE_CHANNEL_SECRET`, `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — webhook service unchanged.

## Security rules

- Never prefix secrets with `NEXT_PUBLIC_`.
- Vercel: mark `SUPABASE_SERVICE_ROLE_KEY` and `LINE_CHANNEL_SECRET` as sensitive; limit to Production/Preview as needed.
- Rotate keys if leaked; update LINE Console + Vercel together.

## Local development matrix

| Profile | Variables |
| ------- | --------- |
| Web only (mock auth — dev optional) | `NEXT_PUBLIC_*` only |
| Full auth local | All web variables + LINE callback `http://localhost:3000` registered |
| Rich menu script | `LINE_CHANNEL_ACCESS_TOKEN`, `DASHBOARD_LIFF_URL` |
