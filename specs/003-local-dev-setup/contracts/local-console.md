# Contract: Local Console Harness

**Feature**: 003-local-dev-setup  
**Entry point**: `python local_run.py`

## Purpose

Simulate LINE text or image message processing locally. Print the bot reply to stdout without calling the LINE Messaging API.

## Command interface

```bash
python local_run.py --text "Lunch 1200 yen"
python local_run.py --image path/to/receipt.jpg
python local_run.py --help
```

| Flag | Required | Description |
| ---- | -------- | ----------- |
| `--text` | one of text/image | Free-form expense message text |
| `--image` | one of text/image | Path to receipt image file |
| `--help` | no | Show usage |

**Rules**:
- `--text` and `--image` are mutually exclusive
- Providing neither prints usage and exits with code 1
- Providing both prints usage and exits with code 1

## Environment

**Required**: `GEMINI_API_KEY`  
**Not required**: `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`  
**Optional**: OCR variables (see [environment-variables.md](./environment-variables.md))

Loads `.env` from project root if present (`python-dotenv`).

## Output contract

| Stream | Content |
| ------ | ------- |
| **stdout** | Final bot reply text only (one message, trailing newline optional) |
| **stderr / logs** | INFO-level processing logs (OCR, intent, errors) |

**Must NOT** call LINE Messaging API `reply_message` or any outbound LINE endpoint.

## Reply parity

For the same input, stdout text MUST equal the text that would be sent to the user via LINE in production (same shared handler as webhook).

## Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | Success; reply printed |
| 1 | Usage error, missing env, unreadable image, or unhandled processing error |

## Examples

**Text expense**:
```bash
$ python local_run.py --text "コーヒー 450円"
Detected expense(s):
- コーヒー: 450.0 JPY
```

**Receipt image**:
```bash
$ python local_run.py --image specs/002-expense-intent-analysis/samples/japanese_receipt.jpg
Detected expense(s):
- ...
```

**Missing GEMINI_API_KEY**:
```bash
Missing required environment variables: GEMINI_API_KEY
```
(exit 1)

## Acceptance checks

| Check | Expected |
| ----- | -------- |
| `--text` with expense | Expense summary on stdout |
| `--text` non-expense | Canned unsupported message on stdout |
| `--image` receipt | Expense summary on stdout |
| `--image` non-receipt | Canned unsupported message on stdout |
| No flags | Usage help, exit 1 |
| No LINE env vars set | Still works if GEMINI_API_KEY set |
