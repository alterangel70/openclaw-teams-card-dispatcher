from __future__ import annotations

from unittest.mock import patch

import httpx

from app.services.graph_client import GraphApiError, GraphClient


class StaticTokenProvider:
    def get_access_token(self) -> str:
        return "token"


def test_send_adaptive_card_reply_success() -> None:
    client = GraphClient(token_provider=StaticTokenProvider(), base_url="https://graph.example.test")

    def fake_post(*_args, **_kwargs):
        return httpx.Response(status_code=201, json={"id": "graph-message-1"})

    with patch("app.services.graph_client.httpx.post", side_effect=fake_post):
        result = client.send_adaptive_card_reply(
            team_id="team-1",
            channel_id="channel-1",
            reply_to_message_id="msg-1",
            adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
        )

    assert result.graph_message_id == "graph-message-1"


def test_send_adaptive_card_reply_non_retriable_error() -> None:
    client = GraphClient(token_provider=StaticTokenProvider(), base_url="https://graph.example.test")

    def fake_post(*_args, **_kwargs):
        return httpx.Response(
            status_code=400,
            json={"error": {"code": "BadRequest", "message": "Invalid payload"}},
        )

    with patch("app.services.graph_client.httpx.post", side_effect=fake_post):
        try:
            client.send_adaptive_card_reply(
                team_id="team-1",
                channel_id="channel-1",
                reply_to_message_id="msg-1",
                adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
            )
            raise AssertionError("Expected GraphApiError to be raised")
        except GraphApiError as exc:
            assert exc.retriable is False
            assert exc.status_code == 400


def test_send_adaptive_card_reply_retriable_error() -> None:
    client = GraphClient(token_provider=StaticTokenProvider(), base_url="https://graph.example.test")

    def fake_post(*_args, **_kwargs):
        return httpx.Response(status_code=503, json={"error": {"message": "Service unavailable"}})

    with patch("app.services.graph_client.httpx.post", side_effect=fake_post):
        try:
            client.send_adaptive_card_reply(
                team_id="team-1",
                channel_id="channel-1",
                reply_to_message_id="msg-1",
                adaptive_card={"type": "AdaptiveCard", "version": "1.4"},
            )
            raise AssertionError("Expected GraphApiError to be raised")
        except GraphApiError as exc:
            assert exc.retriable is True
            assert exc.status_code == 503
