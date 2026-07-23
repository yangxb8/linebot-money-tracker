# Quickstart: Bot Reply Language Override

## Verify bot tests

```bash
python3 -m pytest -q tests/test_user_language.py tests/test_tenant_reply_language.py
```

## Web settings

1. Open the dashboard → Settings → LINE bot behavior.
2. Change **Reply language** to English / Japanese / Chinese / Default.
3. Save.
4. Message the LINE bot (or `python3 local_run.py --text "..."` with Supabase configured for the same tenant) and confirm reply language matches.

## Migration

Apply `supabase/migrations/*_tenant_settings_reply_language.sql` to the Supabase project before deploying bot/web that read the new column.
