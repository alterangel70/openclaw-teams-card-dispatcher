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


def test_build_channel_activity_payload_contains_adaptive_card_attachment() -> None:
    client = _client()

    payload = client.build_channel_activity_payload(
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


def test_build_activity_payload_is_alias_for_channel_payload() -> None:
    """build_activity_payload keeps its old name as a backwards-compat alias."""
    client = _client()
    old = client.build_activity_payload(
        team_id="team-1",
        channel_id="channel-1",
        conversation_id="conversation-1",
        reply_to_message_id="activity-1",
        adaptive_card={"type": "AdaptiveCard"},
    )
    new = client.build_channel_activity_payload(
        team_id="team-1",
        channel_id="channel-1",
        conversation_id="conversation-1",
        reply_to_message_id="activity-1",
        adaptive_card={"type": "AdaptiveCard"},
    )
    assert old == new


def test_build_dm_activity_payload_has_no_channel_data() -> None:
    client = _client()

    payload = client.build_dm_activity_payload(
        conversation_id="8:orgid:user-aad",
        adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
    )

    assert payload["type"] == "message"
    assert "replyToId" not in payload
    assert "channelData" not in payload
    assert payload["conversation"]["id"] == "8:orgid:user-aad"
    assert payload["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"


def test_send_adaptive_card_channel_success_returns_activity_id() -> None:
    client = _client()

    def fake_post(*_args, **_kwargs):
        return httpx.Response(status_code=201, json={"id": "bot-activity-123"})

    with patch("app.services.teams_bot_client.httpx.post", side_effect=fake_post) as mocked_post:
        result = client.send_adaptive_card(
            conversation_type="channel",
            team_id="team-1",
            channel_id="channel-1",
            conversation_id="conversation-1",
            reply_to_message_id="activity-1",
            adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
        )

    # Channel replies use the conversation endpoint without a trailing activity-id;
    # thread routing is carried by the ;messageid= part of the conversation_id.
    assert mocked_post.call_args.args[0].endswith("/v3/conversations/conversation-1/activities")
    assert mocked_post.call_args.args[0].count("/activities/") == 0
    assert result.success is True
    assert result.message_id == "bot-activity-123"
    assert result.error_message is None


def test_send_adaptive_card_dm_success_uses_conversation_activities_url() -> None:
    client = _client()

    def fake_post(*_args, **_kwargs):
        return httpx.Response(status_code=201, json={"id": "dm-activity-456"})

    with patch("app.services.teams_bot_client.httpx.post", side_effect=fake_post) as mocked_post:
        result = client.send_adaptive_card(
            conversation_type="dm",
            conversation_id="8:orgid:user-aad",
            adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
        )

    posted_url = mocked_post.call_args.args[0]
    assert posted_url.endswith("/v3/conversations/8:orgid:user-aad/activities")
    # DM URL must NOT contain a trailing activity id segment
    assert posted_url.count("/activities/") == 0
    assert result.success is True
    assert result.message_id == "dm-activity-456"


def test_send_adaptive_card_dm_payload_has_no_channel_data() -> None:
    client = _client()
    captured: list[dict] = []

    def fake_post(_url, *, headers, json, timeout):
        captured.append(json)
        return httpx.Response(status_code=201, json={"id": "x"})

    with patch("app.services.teams_bot_client.httpx.post", side_effect=fake_post):
        client.send_adaptive_card(
            conversation_type="dm",
            conversation_id="8:orgid:user-aad",
            adaptive_card={"type": "AdaptiveCard"},
        )

    assert "channelData" not in captured[0]
    assert "replyToId" not in captured[0]


def test_send_adaptive_card_retryable_failure() -> None:
    client = _client()

    def fake_post(*_args, **_kwargs):
        return httpx.Response(status_code=503, json={"error": {"message": "Service unavailable"}})

    with patch("app.services.teams_bot_client.httpx.post", side_effect=fake_post):
        result = client.send_adaptive_card(
            conversation_type="channel",
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
            conversation_type="channel",
            team_id="team-1",
            channel_id="channel-1",
            conversation_id="conversation-1",
            reply_to_message_id="activity-1",
            adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
        )

    assert result.success is False
    assert result.retriable is False
    assert "Bad request" in (result.error_message or "")


def test_send_adaptive_card_channel_missing_fields_returns_non_retriable_error() -> None:
    client = _client()

    result = client.send_adaptive_card(
        conversation_type="channel",
        conversation_id="conversation-1",
        adaptive_card={"type": "AdaptiveCard"},
        # team_id, channel_id, reply_to_message_id intentionally omitted
    )

    assert result.success is False
    assert result.retriable is False
    assert result.error_message is not None
