# Teams Card Dispatcher - Executable Technical Backlog

## Implementation Status
- In progress: EPIC 0 - Foundation and Contracts
- Completed in this iteration: T0.1, T0.2, T0.3, T0.4, T0.5, T0.6, T0.7, T0.8, T0.9 (baseline)
- Completed in this iteration: T1.1, T1.2 (ORM model + Alembic migration, including conversation_id)
- Completed in this iteration: T2.1, T2.2, T2.3 (schemas + idempotent service + POST endpoint with required conversationId)
- Completed in this iteration: T3.1, T3.2 (Bot Framework token provider + TeamsBotClient reply delivery)
- Completed in this iteration: T4.1, T4.2 (sequential worker processing + retry state machine)
- Completed in this iteration: T5.1, T5.2 (structured lifecycle logs + Seq validation guide)
- Completed and validated end-to-end: Azure Teams Bot reply delivery to existing Teams thread/message.
- Completed in this iteration: EPIC 6 manual runtime validation (Docker + migrations + API + worker + DB + Teams visual confirmation).
- Completed in this iteration: T6.2 repeatable runtime validation artifacts (`scripts/validate_runtime.sh` + checklist).
- Completed in this iteration: EPIC 7 baseline integration coverage (API idempotency + worker transitions against real PostgreSQL, bot delivery mocked).
- Completed in this iteration: EPIC 7 CI repeatability (GitHub Actions workflow for unit/integration matrix with PostgreSQL service).
- Completed in this iteration: T8.1 operational limits tuning controls + runbook for FAILED recovery.
- Completed in this iteration: EPIC 8 release hardening follow-up (CI quality gates + container build guardrail).
- Next implementation target: Release pipeline extension (container publication and tag-based promotion).

## Scope
This backlog translates the approved implementation plan into actionable tasks with dependencies, acceptance criteria, and verification steps.

## Working Agreements
- All code identifiers must be in English.
- All code comments must be in English.
- API and worker run as separate processes using the same Docker image.
- Dispatch lifecycle states: `PENDING`, `PROCESSING`, `SENT`, `FAILED`.
- v1 uses a single worker instance (no DB row locking strategy yet).

## Definition of Ready (DoR)
A task can start when:
- Inputs and expected outputs are clear.
- Required environment variables are listed.
- Dependencies are complete or mocked.

## Definition of Done (DoD)
A task is done when:
- Code is implemented and follows agreed naming/comment language.
- Local verification steps pass.
- Logs and error paths are covered where applicable.
- Documentation for the task is updated.

---

## EPIC 0 - Foundation and Contracts (Phase 0)
Goal: deliver a runnable baseline with API and worker entrypoints, shared configuration, and structured logging.

### T0.1 - Repository scaffolding
- Type: Setup
- Estimate: S
- Dependencies: None
- Tasks:
1. Create project folders and `__init__.py` files.
2. Add placeholder modules for API routes, worker, services, repositories, models, and schemas.
- Acceptance Criteria:
1. Folder structure exists and imports resolve.
2. `python -m app.main` can import without module errors.

### T0.2 - Python project and dependencies
- Type: Setup
- Estimate: S
- Dependencies: T0.1
- Tasks:
1. Create `pyproject.toml` with runtime dependencies:
   - `fastapi`, `uvicorn[standard]`
   - `sqlalchemy`, `psycopg[binary]`, `alembic`
   - `pydantic-settings`
   - `httpx`, `msal`
   - logging stack for structured logs + Seq sink
2. Add optional dev dependencies: `pytest`, `pytest-asyncio`, `ruff`.
- Acceptance Criteria:
1. Dependencies install successfully.
2. Lint/test tooling commands are available.

### T0.3 - Centralized configuration
- Type: Backend
- Estimate: M
- Dependencies: T0.2
- Tasks:
1. Implement `app/config.py` using `pydantic-settings`.
2. Define strongly-typed settings groups:
   - App (`APP_NAME`, `APP_ENV`, `APP_PORT`)
   - Database (`DATABASE_URL`)
   - Worker (`WORKER_POLL_INTERVAL_SECONDS`, `WORKER_BATCH_SIZE`, `MAX_RETRIES`)
   - Bot (`BOT_APP_ID`, `BOT_APP_PASSWORD`, `BOT_TENANT_ID`, `TEAMS_SERVICE_URL`, `BOT_NAME`)
   - Seq (`SEQ_URL`, `SEQ_API_KEY`, `LOG_LEVEL`)
3. Support `.env` loading and sane defaults for local development.
- Acceptance Criteria:
1. Settings load from `.env` and environment variables.
2. Missing required secrets produce explicit startup errors.

### T0.4 - Logging bootstrap (structured + Seq-ready)
- Type: Backend
- Estimate: M
- Dependencies: T0.3
- Tasks:
1. Add a logging module (`app/logging.py`) for JSON structured logs.
2. Include request correlation fields in log context when available.
3. Configure console output and optional Seq sink controlled by env vars.
- Acceptance Criteria:
1. API and worker both emit structured logs.
2. Seq sink can be enabled via environment variables without code changes.

### T0.5 - FastAPI app bootstrap
- Type: Backend
- Estimate: S
- Dependencies: T0.3, T0.4
- Tasks:
1. Implement `app/main.py` app factory pattern.
2. Register routers and middleware skeleton.
3. Add `GET /health` endpoint.
- Acceptance Criteria:
1. API starts with `uvicorn`.
2. `GET /health` returns HTTP 200 with service metadata.

### T0.6 - Worker process bootstrap
- Type: Backend
- Estimate: S
- Dependencies: T0.3, T0.4
- Tasks:
1. Implement `app/cli/worker.py` entrypoint.
2. Add worker loop skeleton with configurable polling interval.
3. Add graceful shutdown handling.
- Acceptance Criteria:
1. Worker process starts and logs polling cycle heartbeat.
2. Worker stops gracefully on SIGTERM.

### T0.7 - Environment templates
- Type: DevOps
- Estimate: S
- Dependencies: T0.3
- Tasks:
1. Create `.env.example` with all required variables and comments.
2. Keep secret values as placeholders only.
- Acceptance Criteria:
1. `.env.example` is enough to bootstrap local setup after filling values.

### T0.8 - Container baseline (same image, two processes)
- Type: DevOps
- Estimate: M
- Dependencies: T0.2, T0.5, T0.6, T0.7
- Tasks:
1. Create `Dockerfile` for app runtime.
2. Create `docker-compose.yml` with services:
   - `api`
   - `worker`
   - `postgres`
3. Use same image for `api` and `worker`, different commands.
4. Add basic health checks.
- Acceptance Criteria:
1. `docker compose up` starts all services.
2. API health endpoint is reachable.
3. Worker emits heartbeat logs.

### T0.9 - Baseline tests and docs
- Type: QA/Docs
- Estimate: S
- Dependencies: T0.5, T0.6, T0.8
- Tasks:
1. Add smoke tests for API health and worker bootstrap.
2. Create README quickstart for local and Docker usage.
- Acceptance Criteria:
1. Smoke tests pass.
2. README includes run commands and env setup instructions.

---

## EPIC 1 - Persistence and Migration (Phase 1)
Goal: persist dispatch requests with required states and retry metadata.

### T1.1 - ORM model
- Dependencies: EPIC 0 complete
- Tasks:
1. Implement `adaptive_card_dispatches` model with fields:
   - `id`
   - `correlation_id` (unique)
   - `team_id`, `channel_id`, `conversation_id`, `reply_to_message_id`
   - `adaptive_card_json`
   - `status`, `retry_count`, `last_error`, `graph_message_id` (stores bot delivery message/activity id)
   - `next_attempt_at`, `created_at`, `updated_at`, `sent_at`
2. Ensure Teams routing semantics are explicit:
   - `team_id` and `channel_id` are Teams metadata.
   - `conversation_id` is the Bot Framework conversation id required for reply delivery.
   - `reply_to_message_id` is the target Teams activity/message id to reply to.
3. Add status enum for `PENDING`, `PROCESSING`, `SENT`, `FAILED`.
- Acceptance Criteria:
1. ORM model maps correctly to PostgreSQL.

### T1.2 - Alembic migration
- Dependencies: T1.1
- Tasks:
1. Create initial migration.
2. Add indexes for status scheduling queries.
- Acceptance Criteria:
1. Migration up/down works.
2. Unique constraint on `correlation_id` is enforced.

---

## EPIC 2 - Dispatch API (Phase 2)
Goal: receive and persist validated dispatch requests with idempotency.

### T2.1 - Request/response schemas
- Dependencies: EPIC 1 complete
- Tasks:
1. Define schema for:
   - `teamId`, `channelId`, `conversationId`, `replyToMessageId`, `adaptiveCard`, `correlationId`
2. Make `conversationId` required for bot thread replies.
3. Clarify semantics in validation/docs:
   - `teamId`/`channelId` are Teams metadata.
   - `conversationId` is Bot Framework conversation id.
   - `replyToMessageId` is target activity/message id.
4. Add strict validations and clear error messages.
- Acceptance Criteria:
1. Invalid payloads return HTTP 422.

### T2.2 - Idempotent create service
- Dependencies: T2.1
- Tasks:
1. Implement repository + service to create new dispatch in `PENDING`.
2. If `correlationId` exists, return existing record without duplicate insert.
- Acceptance Criteria:
1. Duplicate requests do not create extra rows.

### T2.3 - POST /teams/adaptive-card endpoint
- Dependencies: T2.2
- Tasks:
1. Expose endpoint and wire service.
2. Return `202` for new request and `200/202` for idempotent replay.
- Acceptance Criteria:
1. Endpoint contract matches specification.

---

## EPIC 3 - Azure Teams Bot Reply Delivery (Phase 3)
Goal: send adaptive cards as replies to existing Teams messages via Azure Teams Bot and Bot Framework Connector.

### T3.1 - Bot Framework token provider (MSAL app-only)
- Dependencies: EPIC 0 complete
- Tasks:
1. Implement token acquisition and in-memory caching using:
   - `BOT_APP_ID`
   - `BOT_APP_PASSWORD`
   - `BOT_TENANT_ID`
   - scope `https://api.botframework.com/.default`
- Acceptance Criteria:
1. Token refresh is transparent to caller.

### T3.2 - TeamsBotClient
- Dependencies: T3.1
- Tasks:
1. Implement Bot Framework reply delivery to existing activity using:
   - `POST {TEAMS_SERVICE_URL}/v3/conversations/{conversationId}/activities/{replyToMessageId}`
2. Send Adaptive Card as attachment with:
   - `contentType = application/vnd.microsoft.card.adaptive`
3. Return delivery message id / bot activity id on success.
4. Normalize retriable vs non-retriable errors.
- Acceptance Criteria:
1. Success returns delivery message id / bot activity id.
2. Errors expose retriable/non-retriable classification.

---

## EPIC 4 - Worker Processing (Phase 4)
Goal: sequentially process pending cards and transition state safely in single-worker mode.

### T4.1 - Pending fetch and transition logic
- Dependencies: EPIC 1, EPIC 3 complete
- Tasks:
1. Fetch batch of due `PENDING` rows ordered by `created_at`/`next_attempt_at`.
2. Transition each row to `PROCESSING` before send attempt.
- Acceptance Criteria:
1. Worker processes in deterministic order.

### T4.2 - Send and retry state machine
- Dependencies: T4.1
- Tasks:
1. On success: set `SENT`, `sent_at`, delivery message id / bot activity id (stored in current `graph_message_id` column).
2. On failure with retries left: increment `retry_count`, set `last_error`, compute `next_attempt_at`, return to `PENDING`.
3. On third failure: set `FAILED`.
- Acceptance Criteria:
1. State transitions match approved flow exactly.

---

## EPIC 5 - Observability and Seq (Phase 5)
Goal: ensure traceability for API ingestion and worker dispatch lifecycle.

### T5.1 - Correlation-aware logs
- Dependencies: EPIC 2, EPIC 4 complete
- Tasks:
1. Log lifecycle events with `correlation_id` and status transitions.
2. Include retry metadata in worker error logs.
- Acceptance Criteria:
1. End-to-end flow can be traced from one correlation id.

### T5.2 - Seq validation
- Dependencies: T5.1
- Tasks:
1. Validate logs arriving in Seq using env-provided URL/API key.
- Acceptance Criteria:
1. API and worker logs are visible in Seq.

---

## EPIC 6 - Containerization and Runtime Validation (Phase 6)
Goal: run full stack locally with predictable behavior.

### T6.1 - Manual runtime validation (completed)
- Dependencies: EPIC 4, EPIC 5 complete
- Tasks:
1. Execute end-to-end flow manually and collect evidence:
   - `docker compose up -d --build`
   - `docker compose exec api alembic -c alembic.ini upgrade head`
   - `curl http://localhost:8000/health`
   - `curl -X POST http://localhost:8000/teams/adaptive-card -H 'Content-Type: application/json' -d '{"teamId":"team-1","channelId":"channel-1","conversationId":"conversation-1","replyToMessageId":"msg-1","adaptiveCard":{"type":"AdaptiveCard","version":"1.4","body":[]},"correlationId":"corr-e2e-1"}'`
   - verify worker logs for `PENDING -> PROCESSING -> SENT`
   - verify DB row with `status=SENT`, `retry_count=0`, `last_error=NULL`, `sent_at` populated, delivery id populated
   - verify Teams received adaptive card reply on target thread
- Acceptance Criteria:
1. End-to-end behavior confirmed in Docker runtime with Teams visual verification.

### T6.2 - Repeatable validation script/checklist (completed)
- Dependencies: T6.1
- Tasks:
1. Create a repeatable script/checklist that automates or documents the same validated flow.
2. Standardize evidence outputs (logs, DB query result, HTTP responses).
- Acceptance Criteria:
1. Team can re-run runtime validation consistently with minimal manual interpretation.

---

## EPIC 7 - Tests (Phase 7)
Goal: add confidence for idempotency and state transitions.

### T7.1 - Unit tests
- Dependencies: EPIC 2, EPIC 4 complete
- Tasks:
1. Validate schema and idempotent behavior.
2. Validate retry/backoff and state machine rules.
- Acceptance Criteria:
1. Unit suite passes in CI/local.

### T7.2 - Integration tests
- Dependencies: T7.1
- Tasks:
1. API + PostgreSQL integration tests.
2. Worker processing integration with mocked Teams bot delivery endpoints.
- Acceptance Criteria:
1. Integration suite validates full expected lifecycle.

---

## EPIC 8 - Hardening (Phase 8)
Goal: production-readiness baseline for v1.

### T8.1 - Operational limits and runbook
- Dependencies: EPIC 7 complete
- Tasks:
1. Tune polling interval, batch size, and request timeouts.
2. Document recovery procedure for `FAILED` rows.
- Acceptance Criteria:
1. Runbook includes operational troubleshooting and replay strategy.

---

## Recommended Execution Order (Sprint-friendly)
1. Sprint A: T0.1 to T0.9
2. Sprint B: T1.1, T1.2, T2.1, T2.2, T2.3
3. Sprint C: T3.1, T3.2, T4.1, T4.2 (Azure Teams Bot reply delivery)
4. Sprint D: T5.1, T5.2, T6.1, T6.2, T7.1, T7.2, T8.1

## Immediate Next Action
Implement EPIC 6.2: add a repeatable runtime validation script/checklist based on the already successful manual E2E flow.
