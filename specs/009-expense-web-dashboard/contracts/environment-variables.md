# Contract: Environment Variables

**Feature**: 009-expense-web-dashboard

## Two LINE channels (required by LINE platform)

LINE does **not** allow new LIFF apps on Messaging API channels ([2019 announcement](https://developers.line.biz/en/news/2019/11/11/liff-cannot-be-used-with-messaging-api-channels/)). Use:

| Channel type | Purpose | Credentials used by |
| ------------ | ------- | ------------------- |
| **LINE Login** | Browser Login, LIFF, ID token `sub` | `web/` Next.js app (Vercel) |
| **Messaging API** | Bot webhook, rich menu | Python bot + `scripts/setup_rich_menu.py` |

**Critical**: Create both channels under the **same provider**. LINE assigns the **same user ID** to the same person across Login and Messaging API channels within one provider — this is how dashboard auth maps to `expenses.line_user_id`.

## Web app (`web/.env.local` / Vercel)

| Variable | Required | Exposure | Description |
| -------- | -------- | -------- | ----------- |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Public | `https://nyuenufldaqsjybjhawl.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Public | Supabase publishable/anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | **Server only** | Admin user upsert in auth routes |
| `LINE_LOGIN_CHANNEL_ID` | Yes | Server (+ public client_id in OAuth URL) | **LINE Login channel** (not Messaging API) |
| `LINE_LOGIN_CHANNEL_SECRET` | Yes | **Server only** | **LINE Login channel** secret |
| `NEXT_PUBLIC_LINE_LIFF_ID` | Yes | Public | LIFF app ID on the **LINE Login channel** |
| `NEXT_PUBLIC_APP_URL` | Yes | Public | `https://<app>.vercel.app` or `http://localhost:3000` |

### Optional

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `EXPENSE_PAGE_SIZE` | `20` | Pagination size |

## Bot / rich menu script (Messaging API channel)

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `LINE_CHANNEL_ACCESS_TOKEN` | Yes | Messaging API channel — rich menu create/link API |
| `DASHBOARD_LIFF_URL` | Yes | `https://liff.line.me/{LIFF_ID}` from **Login channel** LIFF app |

## Unchanged bot variables

`LINE_CHANNEL_SECRET` (Messaging API webhook signature), `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — webhook service unchanged.

Note: `LINE_CHANNEL_SECRET` on the bot is **not** the same as `LINE_LOGIN_CHANNEL_SECRET` on the web app when using two channels.

## Security rules

- Never prefix secrets with `NEXT_PUBLIC_`.
- Vercel: mark `SUPABASE_SERVICE_ROLE_KEY` and `LINE_LOGIN_CHANNEL_SECRET` as sensitive.
- Rotate keys if leaked; update LINE Console + Vercel together.

## Local development matrix

| Profile | Variables |
| ------- | --------- |
| Web only (no auth) | `NEXT_PUBLIC_*` only |
| Full auth local | All web variables + Login channel callback `http://localhost:3000` |
| Rich menu script | `LINE_CHANNEL_ACCESS_TOKEN` (bot), `DASHBOARD_LIFF_URL` (Login LIFF) |
