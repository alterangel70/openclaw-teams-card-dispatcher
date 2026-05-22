from __future__ import annotations

from app.config import Settings
from app.services.token_provider import BotTokenProvider


class FakeMsalClient:
    """Small fake client to control token responses in tests."""

    def __init__(self) -> None:
        self.calls = 0

    def acquire_token_for_client(self, scopes):
        self.calls += 1
        return {
            "access_token": "token-value",
            "expires_in": 120,
            "scope": scopes[0],
        }


def _settings() -> Settings:
    return Settings(
        BOT_TENANT_ID="tenant-id",
        BOT_APP_ID="client-id",
        BOT_APP_PASSWORD="secret-value",
    )


def test_get_access_token_uses_cache() -> None:
    provider = BotTokenProvider(_settings())
    fake_client = FakeMsalClient()
    provider._client = fake_client  # type: ignore[attr-defined]

    first = provider.get_access_token()
    second = provider.get_access_token()

    assert first == "token-value"
    assert second == "token-value"
    assert fake_client.calls == 1


def test_missing_bot_settings_raises_error() -> None:
    try:
        BotTokenProvider(Settings())
        raise AssertionError("Expected ValueError to be raised")
    except ValueError as exc:
        assert "BOT_TENANT_ID" in str(exc)
        assert "BOT_APP_ID" in str(exc)
        assert "BOT_APP_PASSWORD" in str(exc)
