# Contract: Rich Menu Setup

**Feature**: 009-expense-web-dashboard  
**Goal**: Persistent bot chat menu item opening the expense dashboard (LIFF)

## Option A — LINE Official Account Manager (no code)

Suitable for quick manual setup.

1. Open [LINE Official Account Manager](https://manager.line.biz/) (or Developers Console → Messaging API → Rich menus).
2. Select the bot's official account linked to your channel.
3. **Rich menus** → **Create**.
4. Configure a single large tile (mobile):
   - **Action type**: Link
   - **URL**: `https://liff.line.me/<LIFF_ID>` (from LIFF tab in Developers Console)
   - **Label**: `家計簿` / `Expenses` (image optional 2500×1686 or 2500×843 px)
5. **Set as default** rich menu for all users (or per-audience if needed).
6. Open a 1:1 chat with the bot → menu should appear at bottom → tap → dashboard loads in LIFF.

### LIFF URL format

```
https://liff.line.me/1234567890-AbCdEfGh
```

Use the LIFF ID from Developers Console → LIFF tab.

## Option B — Messaging API script (repo)

`scripts/setup_rich_menu.py` (to be implemented) calls:

1. `POST https://api.line.me/v2/bot/richmenu` — create menu JSON
2. `POST https://api.line.me/v2/bot/user/all/richmenu/{richMenuId}` — set default

### Rich menu JSON (contract)

```json
{
  "size": { "width": 2500, "height": 843 },
  "selected": true,
  "name": "expense-dashboard-v1",
  "chatBarText": "メニュー",
  "areas": [
    {
      "bounds": { "x": 0, "y": 0, "width": 2500, "height": 843 },
      "action": {
        "type": "uri",
        "label": "家計簿",
        "uri": "https://liff.line.me/{LIFF_ID}"
      }
    }
  ]
}
```

### Script usage

```bash
export LINE_CHANNEL_ACCESS_TOKEN="..."
export DASHBOARD_LIFF_URL="https://liff.line.me/1234567890-AbCdEfGh"
python scripts/setup_rich_menu.py
```

Optional: upload menu image via `POST /v2/bot/richmenu/{richMenuId}/content`.

## Verification checklist

- [ ] Rich menu visible in 1:1 chat (not group-only unless configured)
- [ ] Tap opens LIFF endpoint (`/dashboard` on Vercel)
- [ ] User signs in via LIFF and sees expense list
- [ ] Menu persists after closing and reopening chat

## Notes

- Rich menus apply per **bot** (official account), not per group.
- Group chats show the same user-level rich menu in 1:1; in groups the menu may differ by LINE client version — primary path is **1:1 bot chat**.
- Updating LIFF endpoint URL requires Developers Console save only; rich menu URI can stay `liff.line.me/{id}`.

## Troubleshooting

| Issue | Fix |
| ----- | --- |
| Menu not visible | Ensure default menu is set; wait up to 1 minute; restart LINE app |
| 404 on LIFF | LIFF app published; endpoint URL matches Vercel deploy |
| Opens external browser | Use `liff.line.me` URI, not raw `vercel.app` HTTPS in menu |
