# Contract: Category correction confirmation (YES)

**Feature**: 017-simplify-expense-reply  
**Purpose**: Confirm category guesses before applying edits when user input is not an exact category match.

## Trigger

User replies to a confirmation message with a category that is not an exact match to a known category name.

## Bot behavior

1. Bot guesses the most likely category path.
2. Bot replies with a compact confirmation prompt:
   - Includes the guessed category path
   - Asks the user to reply `YES` to confirm
3. Bot MUST NOT apply the category change until the user confirms.

## Confirmation prompt format (example)

- `カテゴリは「{guessed_category_path}」でOK？ YES で確定`

Localized equivalents should preserve:
- Guessed category path
- Explicit `YES` confirmation requirement

## Outcome

- If user replies `YES`: apply the category edit and return a short “applied” summary.
- If user replies anything else: do not apply; request a clearer category input or allow the user to cancel.
