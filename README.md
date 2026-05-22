# Teams Card Dispatcher

A service that receives Adaptive Card dispatch requests and processes them asynchronously.

## Phase 0 Status
This repository currently includes the baseline implementation:
- FastAPI app bootstrap
- Worker bootstrap with heartbeat loop
- Centralized settings via `.env`
- Structured JSON logging with optional Seq sink
- Docker and Docker Compose baseline

## Requirements
- Python 3.11+
- Docker and Docker Compose (optional but recommended)

## Local Run
1. Create environment file:
   - `cp .env.example .env`
2. Install dependencies:
   - `pip install -e .[dev]`
3. Start API:
   - `uvicorn app.main:app --reload`
4. Start worker (new terminal):
   - `python -m app.cli.worker`

## Docker Run
1. Create environment file:
   - `cp .env.example .env`
2. Start services:
   - `docker compose up --build`
3. Check health endpoint:
   - `curl http://localhost:8000/health`

## Tests
Run smoke tests:
- `pytest`

## Seq Validation
1. Set Seq configuration in `.env`:
   - `SEQ_URL=http://<seq-host>:5341`
   - `SEQ_API_KEY=<optional-api-key>`
2. Start services:
   - `docker compose up --build`
3. Trigger ingestion:
   - `curl -X POST http://localhost:8000/teams/adaptive-card -H 'Content-Type: application/json' -d '{"teamId":"team-1","channelId":"channel-1","replyToMessageId":"msg-1","adaptiveCard":{"type":"AdaptiveCard","version":"1.4","body":[]},"correlationId":"corr-obs-1"}'`
4. In Seq, filter by `correlation_id = 'corr-obs-1'` and confirm lifecycle logs.

Expected structured fields in logs:
- `correlation_id`
- `dispatch_id`
- `status`
- `retry_count`
- `final_status`
- `graph_message_id`

## Next Phases
- Persistence model and Alembic migrations
- Dispatch endpoint with idempotency
- Graph client integration and worker state machine
