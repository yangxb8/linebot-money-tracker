<!--
Sync Impact Report
Version change: TEMPLATE -> 0.1.0
Modified principles:
- [PRINCIPLE_1_NAME] -> Code Quality & Maintainability
- [PRINCIPLE_2_NAME] -> Test-First Delivery
- [PRINCIPLE_3_NAME] -> User Experience Consistency
- [PRINCIPLE_4_NAME] -> Performance & Reliability
- [PRINCIPLE_5_NAME] -> Observability & Feedback
Added sections:
- Additional Constraints
- Development Workflow
Removed sections:
- None
Templates requiring updates:
- .specify/templates/plan-template.md ✅ reviewed
- .specify/templates/spec-template.md ✅ reviewed
- .specify/templates/tasks-template.md ✅ reviewed
- .specify/templates/constitution-template.md ✅ reviewed
Follow-up TODOs: none
-->

# linebot-money-tracker Constitution

## Core Principles

### Code Quality & Maintainability

All production code MUST be modular, readable, and follow the established Python style and project conventions. Complexity MUST be justified by comments and design notes, and duplicated logic MUST be eliminated through clear abstractions.

### Test-First Delivery

All user-facing behavior and expense-tracking logic MUST be defined by automated tests before implementation. Unit tests MUST cover parsing, categorization, validation, and persistence, and integration tests MUST verify LINE webhook handling, AI analysis, and end-to-end expense logging flows.

### User Experience Consistency

Chat responses MUST be consistent, friendly, and clearly communicate both success and failure states. Expense logging, categorization feedback, and monthly analysis outputs MUST follow a predictable structure so users can quickly understand results and next steps.

### Performance & Reliability

The bot MUST respond to user input with low latency and handle malformed text/image input without crashing. Performance-sensitive flows MUST be bounded, with graceful degradation if AI analysis or external services are delayed.

### Observability & Feedback

Application behavior MUST be observable through structured logs, failure reports, and key transaction metrics. User-facing feedback MUST include category decisions and recoverable guidance when the bot cannot confidently classify an expense.

## Additional Constraints

Integration with `line-bot-sdk` is mandatory for LINE webhook handling and event processing. AI categorization and expense analysis MUST be implemented as separate service components so the core bot remains testable and traceable. Secrets and LINE credentials MUST be managed securely and never stored in source control. Expense records MUST be persisted in a recoverable store or file format to avoid data loss.

## Development Workflow

All changes MUST be delivered through pull requests with clear descriptions, test evidence, and constitution compliance notes. Every PR MUST include passing automated tests and a review for UX consistency, error handling, and performance impact. Design decisions that add complexity MUST be documented, and code review MUST enforce the principles in this constitution.

## Governance

This constitution supersedes informal practices for the `linebot-money-tracker` project. Any amendment MUST be documented, reviewed, and accompanied by a version update and an updated amendment date. All pull requests MUST reference the applicable constitution principles to demonstrate compliance, and failing or missing tests MUST block merges.

**Version**: 0.1.0 | **Ratified**: 2026-06-01 | **Last Amended**: 2026-06-01
