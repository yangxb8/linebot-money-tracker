# Feature Specification: Local Development & Cloud Run Setup

**Feature Branch**: `003-local-dev-setup`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "This project is intended to be deployed to google cloud run, however I want to be able to run it locally for testing purpose. Also be specific for the setup I need to do, ex env variables, software I need to install"

## Clarifications

### Session 2026-06-06

- Q: What is the primary local testing workflow? → A: Run the bot logic locally with text or image input simulated as a LINE request; print the bot response to the console instead of sending it through the LINE Messaging API.
- Q: For local console testing, which environment variables are required? → A: Gemini only — `GEMINI_API_KEY` required; LINE variables not needed for console mode.
- Q: How should the local console entry point accept input? → A: Single command with flags — `--text "..."` or `--image path/to/receipt.jpg`.
- Q: What should the console print on success? → A: Reply only — print the final bot message text; standard application logging remains enabled for debug details.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Local console testing without LINE (Priority: P1)

A developer runs the bot's message-handling logic locally by supplying text or a receipt image file. The system treats the input as if it were a LINE message event, processes it through the same expense-detection pipeline used in production, and prints the resulting reply to the console rather than sending it via the LINE bot API.

**Why this priority**: This is the fastest way to iterate on parsing, intent detection, and OCR without configuring tunnels, webhooks, or outbound LINE API calls.

**Independent Test**: Run the documented local console command with `--text` for a text expense message and with `--image` for a receipt file path; verify the expected reply text appears in the terminal and no LINE reply API call is made.

**Acceptance Scenarios**:

1. **Given** a developer runs the console command with `--text "Lunch 1200 yen"`, **When** processing completes, **Then** the bot response is printed to the console and matches what would be sent to the user in production.
2. **Given** a developer runs the console command with `--image path/to/receipt.jpg`, **When** processing completes, **Then** the bot processes the image through the OCR and expense pipeline and prints the detected expense summary to the console.
3. **Given** the local console mode is active, **When** processing completes successfully, **Then** only the final bot reply text is printed to stdout and no reply is sent through the LINE Messaging API.
4. **Given** the developer provides neither `--text` nor `--image`, **When** they run the console command, **Then** usage instructions are printed and the command exits with a non-zero status.
5. **Given** the console command is running, **When** intermediate processing occurs (OCR, intent check, parsing), **Then** debug details are available via standard application logs, not mixed into the stdout reply.

---

### User Story 2 - Run the webhook server locally (Priority: P2)

A developer starts the full webhook server on their machine to verify deployment readiness and optional real LINE integration before Cloud Run.

**Why this priority**: Supports parity with the Cloud Run runtime and optional end-to-end LINE testing, but is secondary to the console harness for day-to-day development.

**Independent Test**: Start the local server and confirm the webhook endpoint responds without startup errors.

**Acceptance Scenarios**:

1. **Given** a developer has installed required software and configured secrets, **When** they start the local server, **Then** the service runs and exposes the webhook endpoint on a documented local port.
2. **Given** required environment variables are missing, **When** the developer starts the service, **Then** the startup fails with a clear message listing which variables are required.

---

### User Story 3 - Test LINE webhook integration from a local machine (Priority: P3)

A developer optionally connects their locally running bot to the LINE Messaging API so real chat events can be exercised during development.

**Why this priority**: Validates the full production integration path but is not required for core local development when using the console harness.

**Independent Test**: Expose the local server via a tunnel, point the LINE webhook URL to it, send a chat message, and verify the bot replies in LINE.

**Acceptance Scenarios**:

1. **Given** the local server is running and a tunnel exposes it over HTTPS, **When** the developer updates the LINE webhook URL to the tunnel address, **Then** LINE can deliver events to the local `/callback` endpoint.
2. **Given** a valid LINE text message is sent to the bot, **When** the webhook is processed locally, **Then** the developer sees a reply in the LINE chat thread.

---

### User Story 4 - Test receipt and image features locally (Priority: P2)

A developer tests expense logging from text and receipt images on their machine, using the same configuration model as production where possible — via the console harness or optional real LINE flow.

**Why this priority**: Image/OCR flows depend on optional local or cloud services; developers need to know what to install or configure to test these paths.

**Independent Test**: Provide a text expense message and a receipt image through the console harness and verify parsed expense output locally.

**Acceptance Scenarios**:

1. **Given** optional OCR software is installed and configured, **When** the developer submits a receipt image via the console harness, **Then** the bot extracts and prints expense details locally.
2. **Given** optional cloud OCR credentials are configured instead of local OCR, **When** the developer submits a receipt image via the console harness, **Then** the bot still processes the image using the configured fallback path.
3. **Given** neither local OCR nor cloud OCR is configured, **When** the developer submits a receipt image that passes intent checks, **Then** the bot prints a clear error rather than failing silently.

---

### User Story 5 - Deploy to Google Cloud Run with documented parity (Priority: P3)

A developer deploys the same application to Google Cloud Run using documented steps, with environment variables and behavior aligned to what was validated locally.

**Why this priority**: Production deployment must be repeatable and consistent with the local setup guide to avoid environment drift.

**Independent Test**: Build and deploy to Cloud Run following the guide, set documented environment variables, and verify the production webhook responds to LINE events.

**Acceptance Scenarios**:

1. **Given** the developer has Google Cloud CLI access and a container image, **When** they deploy to Cloud Run with required environment variables, **Then** the service starts and serves the webhook endpoint over HTTPS.
2. **Given** the service is deployed, **When** the LINE webhook URL is updated to the Cloud Run URL, **Then** the bot behaves the same as during local testing for core text and image flows.

---

### Edge Cases

- Console harness receives input that is not valid text and not a readable image file — print a clear usage or error message.
- Developer runs on Windows, macOS, or Linux — setup instructions must call out platform-specific install steps where they differ (especially for OCR engine installation).
- Developer lacks LINE channel credentials — console harness still works with only `GEMINI_API_KEY`; guide must explain LINE vars are needed only for webhook server and Cloud Run deployment.
- Developer lacks Google Cloud billing or Document AI access — guide must mark cloud OCR as optional and describe the minimum local-only path.
- Tunnel URL changes on restart (common with free tunnel tools) — guide must note that the LINE webhook URL must be updated when the public URL changes.
- Secrets accidentally committed — guide must instruct storing secrets in environment variables or a local `.env` file that is excluded from version control.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The project MUST provide a single, authoritative setup guide that covers local console testing, optional LINE integration, and Google Cloud Run deployment.
- **FR-002**: The setup guide MUST list all required environment variables, their purpose, and whether each is required or optional.
- **FR-003**: The setup guide MUST list all software a developer needs to install, grouped by required vs optional, with version guidance where applicable.
- **FR-004**: A developer MUST be able to run local console testing after following the guide without needing undeclared manual steps.
- **FR-005**: The project MUST provide a local console entry point invoked as a single command with mutually exclusive `--text` or `--image <path>` flags; it simulates a LINE message event, runs the same processing pipeline as production, prints only the final bot reply to stdout, and does not call the LINE Messaging API reply endpoint.
- **FR-013**: Console mode MUST keep standard application logging enabled so developers can inspect OCR, intent, and parsing details in logs without polluting the stdout reply.
- **FR-006**: The setup guide MUST document how to expose the local webhook to LINE (tunnel approach) as an optional end-to-end integration path.
- **FR-007**: The setup guide MUST document how to run automated tests locally without deploying to Cloud Run.
- **FR-008**: The setup guide MUST document Google Cloud Run deployment steps, including how to pass the same environment variables used locally.
- **FR-009**: The setup guide MUST include an example environment file template (e.g. `.env.example`) listing all variables with placeholder values — no real secrets.
- **FR-010**: Optional capabilities (local OCR, cloud Document AI, Japanese language OCR) MUST be documented separately so developers can enable only what they need.
- **FR-011**: Startup validation for the webhook server MUST fail fast with an explicit list of missing required configuration (`LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `GEMINI_API_KEY`).
- **FR-012**: The local console entry point MUST require only `GEMINI_API_KEY` (plus optional OCR variables); it MUST NOT require LINE channel credentials.

### Developer Setup Reference

This section captures the concrete setup the guide MUST document. It reflects the current application capabilities.

#### Required software

| Software | Purpose | Required for |
| -------- | ------- | ------------ |
| Python 3.11+ (3.13 recommended) | Run the application and tests | Local dev, CI |
| pip | Install Python dependencies | Local dev |
| Git | Clone and manage the repository | Local dev |

#### Optional software (enable specific features)

| Software | Purpose | When needed |
| -------- | ------- | ----------- |
| Tesseract OCR + Japanese language pack (`jpn`) | Local receipt OCR via `pytesseract` | Testing image receipts without Document AI |
| Google Cloud SDK (`gcloud`) | Build, deploy, and manage Cloud Run | Cloud Run deployment |
| Docker | Build container images locally | Local container parity with Cloud Run |
| HTTPS tunnel tool (e.g. ngrok, Cloudflare Tunnel) | Expose local webhook to LINE | End-to-end LINE testing on localhost |
| Google Cloud account with Document AI enabled | Cloud OCR fallback for receipts | Testing Document AI path locally or in production |

#### Required environment variables — local console profile

| Variable | Description |
| -------- | ----------- |
| `GEMINI_API_KEY` | Google Gemini API key (intent classification and AI-assisted parsing) |

#### Required environment variables — webhook server / Cloud Run

| Variable | Description |
| -------- | ----------- |
| `LINE_CHANNEL_SECRET` | LINE Messaging API channel secret (validates webhook signatures) |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API channel access token (sends replies) |
| `GEMINI_API_KEY` | Google Gemini API key (intent classification and AI-assisted parsing) |

#### Optional environment variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `TESSERACT_LANG` | `jpn+eng` | Tesseract language(s) for local OCR |
| `DOCUMENT_AI_PROJECT_ID` | — | GCP project ID (falls back to `GOOGLE_CLOUD_PROJECT`) |
| `DOCUMENT_AI_PROCESSOR_ID` | — | Document AI processor ID for cloud OCR |
| `DOCUMENT_AI_LOCATION` | region-specific | Document AI processor region (e.g. `asia-northeast1` for Japan) |
| `GOOGLE_CLOUD_PROJECT` | — | GCP project ID used as fallback for Document AI |

#### Local vs Cloud Run configuration notes

- **Local**: Secrets are typically loaded from a `.env` file or shell environment. Document AI locally requires Application Default Credentials (e.g. `gcloud auth application-default login`).
- **Cloud Run**: Same variable names are set via `--set-env-vars` or the Cloud Run console. Document AI uses the Cloud Run service account; no local ADC file is needed.
- **LINE webhook URL**: Local development uses `https://<tunnel-host>/callback`; Cloud Run uses `https://<cloud-run-url>/callback`.

### Key Entities

- **Environment Configuration**: Named variables and optional files that supply secrets and service settings to the application.
- **Local Console Profile**: Python, pip, and `GEMINI_API_KEY` only — no LINE credentials required.
- **Local Development Profile**: Software and variables needed to run the webhook server locally.
- **Full Integration Profile**: Additional software and variables needed for end-to-end LINE webhook and receipt OCR testing.
- **Cloud Run Deployment Profile**: Container build, GCP project settings, and production environment variables mirroring local configuration.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A new developer can complete local console setup (install software, configure variables, run one text and one image test) in under 30 minutes using only the setup guide.
- **SC-002**: 100% of required environment variables and required software are listed in the setup guide with no undeclared dependencies for basic local console testing.
- **SC-003**: A developer can run the full automated test suite locally in a single documented command without Cloud Run or LINE connectivity.
- **SC-004**: A developer can test text and image expense flows via the console harness, see only the bot reply on stdout, and inspect processing details in application logs — with no LINE API reply call.
- **SC-005**: Cloud Run deployment steps reuse the same environment variable names documented for local development, with zero undocumented production-only variables for core bot functionality.

## Assumptions

- Console stdout shows only the final user-facing reply; structured logs carry debug detail (OCR output, intent decisions, errors).
- Developers have internet access to install packages and call external APIs (Gemini, optional Google Cloud OCR).
- LINE Developers Console access is required only for optional real LINE webhook testing or Cloud Run production use — not for console harness testing.
- Automated tests use mock credentials and do not require real LINE or Gemini keys unless explicitly running integration tests.
- The Docker image used for Cloud Run already includes Tesseract with Japanese support; local developers only need Tesseract if they want local OCR outside Docker.
- Document AI and Gemini usage may incur cloud costs; the guide will note this but cost optimization is out of scope for this feature.
