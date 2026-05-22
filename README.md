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

## Next Phases
- Persistence model and Alembic migrations
- Dispatch endpoint with idempotency
- Graph client integration and worker state machine
