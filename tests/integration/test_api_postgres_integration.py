from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes.dispatch import get_dispatch_service
from app.main import app
from app.models.dispatch import AdaptiveCardDispatch, DispatchStatus
from app.repositories.dispatch_repository import DispatchRepository
from app.services.dispatch_service import DispatchService


@pytest.mark.integration
def test_dispatch_api_idempotency_with_real_postgres(integration_session) -> None:
    """Validate API idempotency against a real PostgreSQL backend."""

    repository = DispatchRepository()

    def _service_override() -> DispatchService:
        return DispatchService(session=integration_session, repository=repository)

    payload = {
        "teamId": "team-itest",
        "channelId": "channel-itest",
        "conversationId": "conversation-itest",
        "replyToMessageId": "reply-itest",
        "adaptiveCard": {"type": "AdaptiveCard", "version": "1.4", "body": []},
        "correlationId": f"itest-api-{int(datetime.now(timezone.utc).timestamp())}",
    }

    app.dependency_overrides[get_dispatch_service] = _service_override
    try:
        with TestClient(app) as client:
            first = client.post("/teams/adaptive-card", json=payload)
            second = client.post("/teams/adaptive-card", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 202
    assert second.status_code == 200

    first_body = first.json()
    second_body = second.json()
    assert first_body["id"] == second_body["id"]

    row = integration_session.query(AdaptiveCardDispatch).filter_by(correlation_id=payload["correlationId"]).one()
    assert row.status == DispatchStatus.PENDING
    assert row.retry_count == 0
