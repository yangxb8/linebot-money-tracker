# Contract: Tenant settings reply language

## GET `/api/settings?tenant_type=&tenant_id=`

Response includes:

```json
{
  "fiscal_start_day": 1,
  "bot_persona_preset": null,
  "bot_persona_custom_text": null,
  "bot_persona_emoji_level": null,
  "confirmation_show_item_details": false,
  "reply_language": null
}
```

`reply_language` is `null` | `"en"` | `"ja"` | `"zh"`.

## PUT `/api/settings`

Body may include `reply_language` with the same allowed values (`null` clears override).

Invalid values → `400` with `invalid_reply_language`.

## Bot resolution

```
base = resolve_reply_language(line_user_id, user_text)
override = tenant_settings.reply_language  # nullable
reply_language = override if override in {en,ja,zh} else base
```
