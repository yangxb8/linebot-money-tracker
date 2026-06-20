# Quickstart: Expense Web Dashboard

## Prerequisites

- Existing bot + Supabase project with migrations through `20260618120000_message_retry.sql` applied
- LINE Developers account with access to the bot's Messaging API channel
- Vercel account (Hobby tier sufficient for MVP)
- Node.js 20+

## 1. LINE Developers Console

### Enable LINE Login (same channel as bot)

1. Open [LINE Developers Console](https://developers.line.biz/console/).
2. Select your provider → select the **same channel** used for the expense bot.
3. Open the **LINE Login** tab (enable Login product on the channel if prompted).
4. Under **Callback URL**, add:
   - `https://<your-vercel-app>.vercel.app/api/auth/line/callback`
   - `http://localhost:3000/api/auth/line/callback` (local dev)
5. Note **Channel ID** and **Channel secret** (Login tab).

### Create LIFF app

1. In the same channel, open the **LIFF** tab → **Add**.
2. **LIFF app name**: `Expense Dashboard` (or similar).
3. **Size**: Full.
4. **Endpoint URL**: `https://<your-vercel-app>.vercel.app/dashboard` (or `/liff` redirect page).
5. **Scopes**: `profile`, `openid`.
6. Note the **LIFF ID** (`liff-xxxxxxxx`).

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
#       SUPABASE_SERVICE_ROLE_KEY, LINE_CHANNEL_ID, LINE_CHANNEL_SECRET,
#       NEXT_PUBLIC_LINE_LIFF_ID, NEXT_PUBLIC_APP_URL=http://localhost:3000

npm install
npm run dev
```

Open `http://localhost:3000/login` for browser LINE Login test.

## 4. Vercel deployment

1. Import the GitHub repo in [Vercel](https://vercel.com/new).
2. Set **Root Directory** to `web` (required — the Next.js app lives in `web/`, not repo root).
3. Add environment variables from [environment-variables.md](./contracts/environment-variables.md).
4. Deploy; update LINE callback URLs and LIFF endpoint to the production `*.vercel.app` URL.

Or use the Vercel CLI from `web/`:

```bash
cd web
vercel link
vercel env pull .env.local
vercel deploy
```

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
| LIFF stuck on loading | LIFF endpoint URL matches deployed `/dashboard`; LIFF ID in env |
| Empty list but bot has data | `line_user_id` in `line_auth_identities` matches `expenses.tenant_id` for personal ledger |
| Group missing from switcher | User must have sent a bot-handled message in that group (`tenant_chat_members` row) |
| 401 on Supabase reads | Session cookie not set; verify Route Handler upserted identity |
