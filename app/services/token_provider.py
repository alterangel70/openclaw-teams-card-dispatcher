"""Token provider implementations for Bot Framework and related integrations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from msal import ConfidentialClientApplication

from app.config import Settings

BOT_FRAMEWORK_SCOPE = "https://api.botframework.com/.default"


class AccessTokenProvider(Protocol):
	"""Protocol for components that can provide bearer tokens."""

	def get_access_token(self) -> str:
		"""Return a valid bearer token for outbound API requests."""


class BotTokenProvider:
	"""MSAL-based token provider for Azure Bot Framework OAuth."""

	def __init__(self, settings: Settings) -> None:
		self._settings = settings
		self._validate_required_settings()

		self._authority = f"https://login.microsoftonline.com/{settings.bot_tenant_id}"
		self._client = ConfidentialClientApplication(
			client_id=settings.bot_app_id,
			client_credential=settings.bot_app_password.get_secret_value(),
			authority=self._authority,
		)

		self._cached_token: str | None = None
		self._expires_at: datetime | None = None

	def get_access_token(self) -> str:
		"""Return a cached token when possible or acquire a new one from MSAL."""

		if self._is_cached_token_valid():
			return self._cached_token  # type: ignore[return-value]

		result = self._client.acquire_token_for_client(scopes=[BOT_FRAMEWORK_SCOPE])
		access_token = result.get("access_token")
		if not access_token:
			error_description = result.get("error_description") or "Token acquisition failed"
			raise RuntimeError(error_description)

		expires_in = int(result.get("expires_in", 3600))
		# Subtract a small safety buffer to avoid expiring during a request.
		self._expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 30, 0))
		self._cached_token = access_token
		return access_token

	def _is_cached_token_valid(self) -> bool:
		"""Check whether the in-memory token is still valid."""

		if not self._cached_token or not self._expires_at:
			return False
		return datetime.now(timezone.utc) < self._expires_at

	def _validate_required_settings(self) -> None:
		"""Ensure Bot auth configuration is present before provider initialization."""

		missing_fields: list[str] = []
		if not self._settings.bot_tenant_id:
			missing_fields.append("BOT_TENANT_ID")
		if not self._settings.bot_app_id:
			missing_fields.append("BOT_APP_ID")
		if not self._settings.bot_app_password.get_secret_value():
			missing_fields.append("BOT_APP_PASSWORD")

		if missing_fields:
			raise ValueError(
				"Missing required Bot auth settings: " + ", ".join(missing_fields),
			)


class MsalTokenProvider(BotTokenProvider):
	"""Backward-compatible alias; use BotTokenProvider for new code."""
