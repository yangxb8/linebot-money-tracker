# Contract: How-to / help intent responses

**Feature**: 017-simplify-expense-reply  
**Purpose**: Define when the bot should answer help/how-to questions instead of rejecting non-expense text.

## Trigger

Inbound user messages that are not expense submissions but ask about:
- changing category
- changing amount
- deleting / restoring
- how to edit a confirmation

## Bot behavior

- Return a short, actionable help response in the user’s reply language.
- Do not require the user to read long instructions; keep to a few examples.
- If the message is unrelated to expense logging/editing, keep existing unsupported behavior.

## Example help response (English)

- `Reply to the confirmation message to edit. Examples: "2 3800", "2 delete", or "Groceries". If I guess the category, reply YES to confirm.`

Localized equivalents should preserve:
- “Reply to the confirmation message”
- 2–3 concrete examples
- Mention of `YES` confirmation when guessing a category
