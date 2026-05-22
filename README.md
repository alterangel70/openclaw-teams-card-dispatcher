# Teams Card Dispatcher

A service that receives Adaptive Card dispatch requests and processes them asynchronously.

## Delivery Architecture
Runtime delivery path:

OpenClaw -> FastAPI API -> PostgreSQL -> Worker -> Azure Teams Bot -> Teams

The worker sends Adaptive Cards through Bot Framework proactive messaging so the message author in Teams is the bot identity.
The dispatcher sends cards as replies to existing messages/threads, not as new channel posts.

## Phase 0 Status
This repository currently includes the baseline implementation:
- FastAPI app bootstrap
- Worker processing loop with retries and state machine
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

## Bot Configuration
Required bot variables in `.env`:
- `BOT_APP_ID`
- `BOT_APP_PASSWORD`
- `BOT_TENANT_ID`
- `TEAMS_SERVICE_URL`
- `BOT_NAME` (optional display name override)

Important notes:
- The bot must be installed in the target Team/channel.
- Dispatch request must include `conversationId` (Bot Framework conversation id).
- `channelId` is the Teams channel id (not used as conversation id).
- `replyToMessageId` is used as `replyToId` and as the target activity id in the reply endpoint.
- Graph chatMessage APIs are not used for runtime dispatch delivery.

## Dispatch Request Notes
Required fields for reply delivery:
- `teamId`
- `channelId`
- `conversationId`
- `replyToMessageId`
- `adaptiveCard`
- `correlationId`

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
   - `curl -X POST http://localhost:8000/teams/adaptive-card -H 'Content-Type: application/json' -d '{"teamId":"team-1","channelId":"channel-1","conversationId":"conversation-1","replyToMessageId":"msg-1","adaptiveCard":{"type":"AdaptiveCard","version":"1.4","body":[]},"correlationId":"corr-obs-1"}'`
4. In Seq, filter by `correlation_id = 'corr-obs-1'` and confirm lifecycle logs.

Expected structured fields in logs:
- `correlation_id`
- `dispatch_id`
- `status`
- `retry_count`
- `final_status`
- `graph_message_id`

## Next Phases
- Runtime validation and container hardening
