# Contract: Bot Functional Suite

**Feature**: 021-automated-functional-tests  
**Surface**: LINE bot FastAPI webhook  
**Lane**: `pr_fast`

## Entry point

- `POST /callback`
- Header: `X-Line-Signature` (HMAC-SHA256 over raw body with `LINE_CHANNEL_SECRET`, base64 — as produced by LINE Messaging API / `line-bot-sdk` WebhookParser)
- Body: LINE webhook JSON (`{"destination":"...","events":[...]}`)

## Shared test fixtures

- `LINE_CHANNEL_SECRET=test_secret`, `LINE_CHANNEL_ACCESS_TOKEN=test_token`, `GEMINI_API_KEY=test_gemini_key`
- `line_bot_api.reply_message` mocked (`AsyncMock`)
- Gemini / intent / persist patched at the same service boundaries used by unit tests (no live network)

## Scenario contracts

### `bot.webhook.unsigned`

| | |
| --- | --- |
| **Given** | Body present; signature missing or invalid |
| **When** | `POST /callback` |
| **Then** | HTTP `400`; `reply_message` not called |

### `bot.expense.text_confirm`

| | |
| --- | --- |
| **Given** | Valid signature; text message event with expense-like text; AI/parse mocks return one expense item |
| **When** | `POST /callback` |
| **Then** | HTTP `200`/`OK`; `reply_message` awaited once with confirmation-style text; expense insert and/or pending confirmation side effects asserted (exact mock targets match current `message_handler` seams) |

### `bot.expense.reply_edit`

| | |
| --- | --- |
| **Given** | Prior confirmation/pending expense state prepared via mocks; reply event referencing bot message with new amount text |
| **When** | `POST /callback` |
| **Then** | Reply reflects updated amount; expense mutation mock called accordingly |

### `bot.wish.accept`

| | |
| --- | --- |
| **Given** | Wish intent path produces pending `wish_list_add`; subsequent yes reply |
| **When** | Suites run propose + affirm (one or two webhook posts as needed) |
| **Then** | Wish-list insert mock called; expense insert **not** called |

### `bot.wish.decline`

| | |
| --- | --- |
| **Given** | Same pending wish as accept path; no/cancel reply |
| **When** | Affirmation declined |
| **Then** | Neither wish insert nor expense insert called |

## Non-goals (v1)

- Image/receipt message events
- Real Gemini or LINE network I/O
- Asserting full persona/emoji-rendered copy character-by-character

## Local command

```bash
python3 -m pytest -q tests/functional/bot
```
