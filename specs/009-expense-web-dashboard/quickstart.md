# Quickstart: Expense Web Dashboard

## Prerequisites

- Existing bot + Supabase project with migrations through `20260618120000_message_retry.sql` applied
- LINE Developers account with access to the bot's Messaging API channel
- Vercel account (Hobby tier sufficient for MVP)
- Node.js 20+

## 1. LINE Developers Console

### Create a LINE Login channel (LIFF cannot use Messaging API channel)

Per [LINE's 2019 policy](https://developers.line.biz/en/news/2019/11/11/liff-cannot-be-used-with-messaging-api-channels/), LIFF apps must be added to a **LINE Login channel**, not your Messaging API bot channel.

1. Open [LINE Developers Console](https://developers.line.biz/console/).
2. Select the **same provider** as your expense bot's Messaging API channel (required so user IDs match).
3. **Create a new channel** → type **LINE Login**.
4. Under **Callback URL**, add:
   - `https://<your-vercel-app>.vercel.app/api/auth/line/callback`
   - `http://localhost:3000/api/auth/line/callback` (local dev)
5. Note **Channel ID** and **Channel secret** from this **Login channel** → use as `LINE_LOGIN_CHANNEL_ID` / `LINE_LOGIN_CHANNEL_SECRET` in Vercel.

### Create LIFF app (on the Login channel)

1. On the **LINE Login channel**, open the **LIFF** tab → **Add**.
2. **LIFF app name**: `Expense Dashboard` (or similar).
3. **Size**: Full.
4. **Endpoint URL**: `https://<your-vercel-app>.vercel.app/dashboard`
5. **Scopes**: `profile`, `openid`.
6. Note the **LIFF ID** → `NEXT_PUBLIC_LINE_LIFF_ID`.

### Bot channel (unchanged)

Your existing **Messaging API** channel continues to run the bot webhook. Rich menu uses `LINE_CHANNEL_ACCESS_TOKEN` from this channel; the menu action URL points to the **Login channel** LIFF URL (`https://liff.line.me/<LIFF_ID>`).

### Supabase Auth redirect URLs

In Supabase Dashboard → Authentication → URL Configuration:

- **Site URL**: `https://<your-vercel-app>.vercel.app`
- **Redirect URLs**: add the Vercel app origin and `http://localhost:3000`

## 2. Supabase migration

Migration `20260619120000_web_dashboard_auth_rls.sql` adds `line_auth_identities`, `current_line_user_id()`, and RLS policies for the web dashboard.

```bash
# From repo root
supabase db push
# or apply supabase/migrations/20260619120000_web_dashboard_auth_rls.sql via Supabase MCP/CLI
```

Verify helper function (SQL editor, unauthenticated):

```sql
SELECT current_line_user_id(); -- Expected: NULL
```

**Verified 2026-06-20**: `current_line_user_id()` returns `NULL` when unauthenticated in SQL editor.

## 3. Local web development

```bash
cd web
cp .env.example .env.local
# Fill: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY,
#       SUPABASE_SERVICE_ROLE_KEY, LINE_LOGIN_CHANNEL_ID, LINE_LOGIN_CHANNEL_SECRET,
#       NEXT_PUBLIC_LINE_LIFF_ID, NEXT_PUBLIC_APP_URL=http://localhost:3000

npm install
npm run dev
```

Open `http://localhost:3000/login` for browser LINE Login test.

## 4. Vercel deployment

1. Import the GitHub repo in [Vercel](https://vercel.com/new).
2. Set **Root Directory** to `web` (required — the Next.js app lives in `web/`, not repo root).
3. Confirm **Framework Preset** is **Next.js** (repo includes `web/vercel.json` to enforce this).
4. Leave **Output Directory** empty (Next.js default).
5. Add environment variables from [environment-variables.md](./contracts/environment-variables.md).
6. Set `NEXT_PUBLIC_APP_URL=https://linebot-money-tracker.vercel.app` (your production URL).
7. Deploy; update LINE callback URLs and LIFF endpoint to the production URL.

Or use the Vercel CLI from `web/`:

```bash
cd web
vercel link
vercel env pull .env.local
vercel deploy
```

### Troubleshooting 404 on `*.vercel.app`

| Symptom | Fix |
| ------- | --- |
| `NOT_FOUND` on `/` | Root Directory must be `web`, not repo root |
| Build succeeds but all routes 404 | Framework Preset must be **Next.js**; redeploy after setting |
| Preview URLs ask for Vercel login | Disable **Deployment Protection** for Production (Settings → Deployment Protection) so LINE/LIFF can reach the app |

## 5. Rich menu (bot discovery)

See [rich-menu-setup.md](./contracts/rich-menu-setup.md) for LINE Console steps and optional script:

```bash
export LINE_CHANNEL_ACCESS_TOKEN=...
export DASHBOARD_LIFF_URL=https://<liff-id>.liff.line.me
python scripts/setup_rich_menu.py
```

## 6. End-to-end verification

### Personal ledger

1. Log an expense in 1:1 chat with the bot: `スーパー 1500円`.
2. Open dashboard (browser Login or LIFF rich menu).
3. Confirm personal ledger shows the expense with date, description, amount, category.

### Group ledger

1. Log an expense in a group where you are a member.
2. In dashboard, switch tenant to that group.
3. Confirm shared expenses appear.

### Security spot check

Sign in as user A; confirm user B's personal expenses are not visible. Attempt direct Supabase client query with another user's tenant filter — RLS should return zero rows. See `tests/web/rls_policies.test.sql` for policy documentation.

**RLS verification (2026-06-20)**: Migration applied; `current_line_user_id()` returns NULL unauthenticated. Cross-tenant denial must be confirmed via authenticated Supabase JS client during pilot testing.

### Language

Set bot language via existing preference flow; reload dashboard — UI strings should match `ja` / `en` / `zh`.

## 7. SQL debugging

```sql
-- Link table after sign-in
SELECT * FROM line_auth_identities WHERE line_user_id = '<LINE_USER_ID>';

-- Tenants for user
SELECT * FROM tenant_chat_members WHERE line_user_id = '<LINE_USER_ID>';

-- Expenses visible under RLS (run as authenticated user via Supabase client, not SQL editor)
```

## Troubleshooting

| Symptom | Check |
| ------- | ----- |
| OAuth redirect mismatch | LINE Console callback URL exactly matches Vercel route |
| Site shows `NOT_FOUND` on `/` | Vercel Root Directory = `web`, Framework = Next.js, redeploy |
| LIFF stuck on loading | LIFF endpoint URL matches deployed `/dashboard`; LIFF ID in env |
| Empty list but bot has data | `line_user_id` in `line_auth_identities` matches `expenses.tenant_id` for personal ledger |
| Group missing from switcher | User must have sent a bot-handled message in that group (`tenant_chat_members` row) |
| 401 on Supabase reads | Session cookie not set; verify Route Handler upserted identity |
