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


def _valid_channel_payload() -> dict:
    return {
        "conversationType": "channel",
        "teamId": "team-123",
        "channelId": "channel-123",
        "conversationId": "19:abc123xyz@thread.tacv2",
        "replyToMessageId": "message-123",
        "adaptiveCard": {"type": "AdaptiveCard", "version": "1.4", "body": []},
        "correlationId": "corr-123",
    }


def _valid_dm_payload() -> dict:
    return {
        "conversationType": "dm",
        "conversationId": "8:orgid:user-aad-object-id",
        "adaptiveCard": {"type": "AdaptiveCard", "version": "1.4", "body": []},
        "correlationId": "corr-dm-123",
    }


# Backwards-compat alias used by existing tests below.
_valid_payload = _valid_channel_payload


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


def test_create_dispatch_dm_returns_202() -> None:
    fake_service = FakeDispatchService()
    app.dependency_overrides[get_dispatch_service] = lambda: fake_service

    try:
        with TestClient(app) as client:
            response = client.post("/teams/adaptive-card", json=_valid_dm_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["correlationId"] == "corr-dm-123"
    assert body["status"] == "PENDING"


def test_create_dispatch_channel_missing_team_id_returns_422() -> None:
    """conversationType=channel requires teamId, channelId and replyToMessageId."""
    fake_service = FakeDispatchService()
    app.dependency_overrides[get_dispatch_service] = lambda: fake_service

    payload = _valid_channel_payload()
    payload.pop("teamId")

    try:
        with TestClient(app) as client:
            response = client.post("/teams/adaptive-card", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_create_dispatch_dm_without_channel_fields_accepted() -> None:
    """DM dispatches must succeed even when teamId/channelId/replyToMessageId are absent."""
    fake_service = FakeDispatchService()
    app.dependency_overrides[get_dispatch_service] = lambda: fake_service

    payload = {
        "conversationType": "dm",
        "conversationId": "8:orgid:user-aad",
        "adaptiveCard": {"type": "AdaptiveCard", "version": "1.4"},
        "correlationId": "corr-dm-no-channel-fields",
    }

    try:
        with TestClient(app) as client:
            response = client.post("/teams/adaptive-card", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202


def test_conversation_id_bot_framework_wrapper_is_normalised() -> None:
    """conversation:19:xxx@thread.tacv2;messageid=123 prefix is stripped, messageid kept."""
    fake_service = FakeDispatchService()
    app.dependency_overrides[get_dispatch_service] = lambda: fake_service

    payload = _valid_channel_payload()
    payload["conversationId"] = "conversation:19:abc123xyz@thread.tacv2;messageid=1779713946395"

    try:
        with TestClient(app) as client:
            response = client.post("/teams/adaptive-card", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202


def test_conversation_id_invalid_format_returns_422() -> None:
    """An unrecognised conversation ID format that cannot be normalised returns 422."""
    fake_service = FakeDispatchService()
    app.dependency_overrides[get_dispatch_service] = lambda: fake_service

    payload = _valid_channel_payload()
    payload["conversationId"] = "totally-wrong-id"

    try:
        with TestClient(app) as client:
            response = client.post("/teams/adaptive-card", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422