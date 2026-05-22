from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.routes.dispatch import get_dispatch_service
from app.main import app
from app.models.dispatch import DispatchStatus


class FakeDispatchService:
    """In-memory fake service for endpoint behavior validation."""

    def __init__(self) -> None:
        self._records: dict[str, SimpleNamespace] = {}
        self._next_id = 1

    def create_or_get_dispatch(self, payload):
        existing = self._records.get(payload.correlation_id)
        if existing is not None:
            return existing, False

        now = datetime.now(timezone.utc)
        created = SimpleNamespace(
            id=self._next_id,
            correlation_id=payload.correlation_id,
            status=DispatchStatus.PENDING,
            retry_count=0,
            created_at=now,
            updated_at=now,
        )
        self._next_id += 1
        self._records[payload.correlation_id] = created
        return created, True


def _valid_payload() -> dict:
    return {
        "teamId": "team-123",
        "channelId": "channel-123",
        "conversationId": "conversation-123",
        "replyToMessageId": "message-123",
        "adaptiveCard": {"type": "AdaptiveCard", "version": "1.4", "body": []},
        "correlationId": "corr-123",
    }


def test_create_dispatch_returns_202_for_new_record() -> None:
    fake_service = FakeDispatchService()
    app.dependency_overrides[get_dispatch_service] = lambda: fake_service

    try:
        with TestClient(app) as client:
            response = client.post("/teams/adaptive-card", json=_valid_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["correlationId"] == "corr-123"
    assert body["status"] == "PENDING"
    assert body["retryCount"] == 0


def test_create_dispatch_returns_200_for_idempotent_replay() -> None:
    fake_service = FakeDispatchService()
    app.dependency_overrides[get_dispatch_service] = lambda: fake_service

    try:
        with TestClient(app) as client:
            first = client.post("/teams/adaptive-card", json=_valid_payload())
            second = client.post("/teams/adaptive-card", json=_valid_payload())
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["correlationId"] == first.json()["correlationId"]
    assert second.json()["id"] == first.json()["id"]


def test_create_dispatch_returns_422_for_invalid_payload() -> None:
    fake_service = FakeDispatchService()
    app.dependency_overrides[get_dispatch_service] = lambda: fake_service

    invalid_payload = _valid_payload()
    invalid_payload.pop("teamId")

    try:
        with TestClient(app) as client:
            response = client.post("/teams/adaptive-card", json=invalid_payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_create_dispatch_returns_422_when_conversation_id_missing() -> None:
    fake_service = FakeDispatchService()
    app.dependency_overrides[get_dispatch_service] = lambda: fake_service

    invalid_payload = _valid_payload()
    invalid_payload.pop("conversationId")

    try:
        with TestClient(app) as client:
            response = client.post("/teams/adaptive-card", json=invalid_payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422