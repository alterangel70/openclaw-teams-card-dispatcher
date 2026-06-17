# Operations Runbook

## Scope
This runbook covers routine operation, troubleshooting, and recovery for dispatch rows that end in `FAILED`.

## Runtime Control Variables
Use these variables to tune operational behavior without code changes:

- `WORKER_POLL_INTERVAL_SECONDS` (default: `5`, allowed: `1-300`)
- `WORKER_BATCH_SIZE` (default: `50`, allowed: `1-500`)
- `MAX_RETRIES` (default: `3`, allowed: `1-10`)
- `BOT_REQUEST_TIMEOUT_SECONDS` (default: `20`, allowed: `1-120`)

## Steady-State Checks
1. API health check:
   - `curl http://localhost:8000/health`
2. Worker logs:
   - `docker compose logs --since 5m worker`
3. Queue status by state:
   - `docker compose exec -T postgres psql -U postgres -d teams_dispatcher -c "SELECT status, COUNT(*) FROM adaptive_card_dispatches GROUP BY status ORDER BY status;"`

## Incident Triage for FAILED Rows
1. Identify recent failures:
   - `docker compose exec -T postgres psql -U postgres -d teams_dispatcher -c "SELECT id, correlation_id, retry_count, last_error, updated_at FROM adaptive_card_dispatches WHERE status='FAILED' ORDER BY updated_at DESC LIMIT 50;"`
2. Group by dominant error:
   - `docker compose exec -T postgres psql -U postgres -d teams_dispatcher -c "SELECT last_error, COUNT(*) FROM adaptive_card_dispatches WHERE status='FAILED' GROUP BY last_error ORDER BY COUNT(*) DESC LIMIT 10;"`
3. Confirm connector/auth settings in environment:
   - `BOT_APP_ID`, `BOT_APP_PASSWORD`, `BOT_TENANT_ID`, `TEAMS_SERVICE_URL`

## Recovery Strategies
Use one strategy at a time, based on root cause.

### Strategy A: Requeue existing FAILED rows
Use when payload/routing is still valid and failure was transient.

1. Requeue selected rows:
   - `docker compose exec -T postgres psql -U postgres -d teams_dispatcher -c "UPDATE adaptive_card_dispatches SET status='PENDING', next_attempt_at=NOW(), last_error=NULL, updated_at=NOW() WHERE status='FAILED' AND id IN (<comma_separated_ids>);"`
2. Monitor worker logs for transition `PENDING -> PROCESSING -> SENT`.

### Strategy B: Submit a fresh dispatch
Use when routing or payload must change.

1. Re-submit through API with a new `correlationId`.
2. Keep original failed row for audit history.

## Safety Rules
1. Do not bulk reset all `FAILED` rows without filtering by a known incident window.
2. Prefer smaller replay batches first (for example 20-50 rows).
3. Verify downstream Teams behavior before scaling replay.

## Post-Incident Validation
1. Confirm `FAILED` count trend is down.
2. Confirm new dispatches are reaching `SENT` with populated `sent_at`.
3. Capture correlation ids and root cause summary in incident notes.
