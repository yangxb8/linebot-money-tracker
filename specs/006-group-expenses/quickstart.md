# Quickstart: Group Shared Expenses

## Local testing

Personal (unchanged):

```bash
python local_run.py --text "Lunch 1200円"
```

Group shared ledger:

```bash
python local_run.py --group-id "test-group-1" --text "Lunch 1200円"
```

Reply-edit in group (use another `LOCAL_LINE_USER_ID` to simulate a different member):

```bash
LOCAL_LINE_USER_ID=member-b python local_run.py --group-id "test-group-1" --reply-to <bot_message_id> --text "3800円"
```

## Apply migration

Run `supabase/migrations/20260608120000_group_expenses.sql` against the Supabase project before deploying.
