from __future__ import annotations

from unittest.mock import patch

import httpx

from app.services.teams_bot_client import TeamsBotClient


class StaticTokenProvider:
    def get_access_token(self) -> str:
        return "token"


def _client() -> TeamsBotClient:
    return TeamsBotClient(
        token_provider=StaticTokenProvider(),
        service_url="https://smba.trafficmanager.net/amer/",
        bot_app_id="bot-app-id",
        bot_name="OpenClaw Bot",
    )


def test_build_activity_payload_contains_adaptive_card_attachment() -> None:
    client = _client()

    payload = client.build_activity_payload(
        team_id="team-1",
        channel_id="channel-1",
        conversation_id="conversation-1",
        reply_to_message_id="activity-1",
        adaptive_card={"type": "AdaptiveCard", "version": "1.4", "body": []},
    )

    assert payload["type"] == "message"
    assert payload["replyToId"] == "activity-1"
    assert payload["conversation"]["id"] == "conversation-1"
    assert payload["channelData"]["channel"]["id"] == "channel-1"
    assert payload["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"


def test_send_adaptive_card_success_returns_activity_id() -> None:
    client = _client()

    def fake_post(*_args, **_kwargs):
        return httpx.Response(status_code=201, json={"id": "bot-activity-123"})

    with patch("app.services.teams_bot_client.httpx.post", side_effect=fake_post) as mocked_post:
        result = client.send_adaptive_card(
            team_id="team-1",
            channel_id="channel-1",
            conversation_id="conversation-1",
            reply_to_message_id="activity-1",
            adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
        )

    assert mocked_post.call_args.args[0].endswith("/v3/conversations/conversation-1/activities/activity-1")

    assert result.success is True
    assert result.message_id == "bot-activity-123"
    assert result.error_message is None


def test_send_adaptive_card_retryable_failure() -> None:
    client = _client()

    def fake_post(*_args, **_kwargs):
        return httpx.Response(status_code=503, json={"error": {"message": "Service unavailable"}})

    with patch("app.services.teams_bot_client.httpx.post", side_effect=fake_post):
        result = client.send_adaptive_card(
            team_id="team-1",
            channel_id="channel-1",
            conversation_id="conversation-1",
            reply_to_message_id="activity-1",
            adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
        )

    assert result.success is False
    assert result.retriable is True
    assert result.error_message is not None


def test_send_adaptive_card_non_retryable_failure() -> None:
    client = _client()

    def fake_post(*_args, **_kwargs):
        return httpx.Response(status_code=400, json={"error": {"message": "Bad request"}})

    with patch("app.services.teams_bot_client.httpx.post", side_effect=fake_post):
        result = client.send_adaptive_card(
            team_id="team-1",
            channel_id="channel-1",
            conversation_id="conversation-1",
            reply_to_message_id="activity-1",
            adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
        )

    assert result.success is False
    assert result.retriable is False
    assert "Bad request" in (result.error_message or "")
