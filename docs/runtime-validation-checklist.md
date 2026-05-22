# Runtime Validation Checklist

Use this checklist with `scripts/validate_runtime.sh` to capture repeatable evidence.

## Preconditions
- `.env` exists and contains valid bot credentials.
- Bot is installed in target Team/channel.
- You have valid values for:
  - `teamId`
  - `channelId`
  - `conversationId`
  - `replyToMessageId`

## Run
```bash
scripts/validate_runtime.sh \
  --team-id "<team_id>" \
  --channel-id "<channel_id>" \
  --conversation-id "<conversation_id>" \
  --reply-to-message-id "<reply_to_message_id>"
```

## Evidence to collect
- Docker compose startup success.
- Alembic upgrade success.
- `GET /health` returns 200.
- `POST /teams/adaptive-card` returns 202 (or 200 for replay).
- Worker logs include transition to `SENT`.
- DB row has:
  - `status = SENT`
  - `retry_count = 0`
  - `last_error = null/empty`
  - `graph_message_id` populated (delivery activity id)
  - `sent_at` populated
- Teams UI shows adaptive card as reply to the target message/thread.

## Pass/Fail
- Pass when all evidence above is satisfied.
- Fail if DB ends in `FAILED`, times out without `SENT`, or Teams UI reply is missing.
