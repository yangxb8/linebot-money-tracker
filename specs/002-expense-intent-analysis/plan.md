# Implementation Plan: Expense Intent Analysis

**Branch**: `002-expense-intent-analysis` | **Date**: 2026-06-02 | **Spec**: `/specs/002-expense-intent-analysis/spec.md`

**Input**: Feature specification from `/specs/002-expense-intent-analysis/spec.md`

## Summary

Enhance the existing LINE bot to analyze incoming user input before processing it. The implementation will accept expense submissions only, via free-form text or receipt images, and it will reject unsupported requests with a fixed canned reply to reduce AI usage. For valid expense requests, the bot will return a plain-text expense summary, listing each item separately when multiple expenses are detected.

## Technical Context

**Language/Version**: Python 3.13+ (current project uses Python with FastAPI)

**Primary Dependencies**: FastAPI, line-bot-sdk, google-genai, pytest, pytest-asyncio

**Storage**: N/A for this feature; expense detection returns text only and does not persist transaction records in this phase.

**Testing**: pytest with `pytest-asyncio` for webhook and parser tests, plus targeted unit tests for intent detection and image handling behavior.

**Target Platform**: Cloud-hosted Python web service with HTTPS-accessible LINE webhook endpoint.

**Project Type**: web-service

**Performance Goals**: valid expense submissions should be analyzed and replied to within 5 seconds; unsupported requests should be rejected with a canned reply without additional AI consumption.

**Constraints**: must preserve LINE webhook security and secrets via environment variables, support only text and image expense inputs, and avoid processing unrelated requests.

**Scale/Scope**: MVP-level expense logging intake for early validation; not a full transaction ledger or multi-user financial system.

## Constitution Check

This plan remains aligned with the repository constitution by prioritizing a minimal, testable implementation, avoiding unnecessary scope expansion, and using explicit behavior for unsupported inputs. The feature will be delivered with structured logging, input validation, and a clear fallback path.

## Project Structure

### Documentation (this feature)

```text
specs/002-expense-intent-analysis/
├── spec.md
├── plan.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
main.py
requirements.txt
README.md
services/
tests/
```

**Structure Decision**: Keep the existing root-level service layout. Implement feature-specific business logic in service modules and add focused tests under `tests/` to avoid adding unnecessary project structure.

## Implementation Approach

1. Validate and parse LINE webhook events in `main.py`.
2. Add an expense intent analyzer that checks whether incoming text or image input is an expense logging request.
3. For text input:
   - Analyze the message content
   - If it is a valid expense request, extract expense details and return them in plain text
   - If not, reply with a fixed canned message explaining that only text/image expense logging is supported
4. For image input:
   - Accept receipt images
   - Use the agent or OCR-assisted model to extract expense items from the image
   - Return each detected expense separately in plain text
5. For unsupported event types or non-expense content:
   - Respond with a fixed canned message rather than invoking AI analysis
6. Preserve original amounts, currency, and merchant context in the returned summary.

## Risks and Open Questions

- Image extraction accuracy depends on the AI/OCR model and may require future refinement; the hybrid flow reduces per-image AI usage but still relies on OCR quality.
- Future request types such as budgeting or analytics are deliberately out of scope for this iteration.
- The plan assumes the existing bot architecture can be extended cleanly with an intent/expense analyzer and that OCR libraries (or cloud Vision) will be available in the deployment environment.

## Next Steps

- Create `research.md` if needed for clarifying the best approach to image expense extraction and model prompts.
- Add `data-model.md` if entity modeling becomes necessary for the expense detection flow.
- Generate `tasks.md` to break the implementation into concrete development steps.
