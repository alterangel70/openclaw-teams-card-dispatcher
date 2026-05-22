"""Token provider implementation for Microsoft Graph app-only auth."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from msal import ConfidentialClientApplication

from app.config import Settings


class AccessTokenProvider(Protocol):
	"""Protocol for components that can provide a Graph bearer token."""

	def get_access_token(self) -> str:
		"""Return a valid bearer token for Graph API requests."""


class MsalTokenProvider:
	"""MSAL-based token provider using OAuth client credentials flow."""

	def __init__(self, settings: Settings) -> None:
		self._settings = settings
		self._validate_required_settings()

		self._authority = f"https://login.microsoftonline.com/{settings.graph_tenant_id}"
		self._client = ConfidentialClientApplication(
			client_id=settings.graph_client_id,
			client_credential=settings.graph_client_secret.get_secret_value(),
			authority=self._authority,
		)

		self._cached_token: str | None = None
		self._expires_at: datetime | None = None

	def get_access_token(self) -> str:
		"""Return a cached token when possible or acquire a new one from MSAL."""

		if self._is_cached_token_valid():
			return self._cached_token  # type: ignore[return-value]

		result = self._client.acquire_token_for_client(scopes=[self._settings.graph_scope])
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
		"""Ensure Graph auth configuration is present before provider initialization."""

		missing_fields: list[str] = []
		if not self._settings.graph_tenant_id:
			missing_fields.append("GRAPH_TENANT_ID")
		if not self._settings.graph_client_id:
			missing_fields.append("GRAPH_CLIENT_ID")
		if not self._settings.graph_client_secret.get_secret_value():
			missing_fields.append("GRAPH_CLIENT_SECRET")

		if missing_fields:
			raise ValueError(
				"Missing required Graph auth settings: " + ", ".join(missing_fields),
			)
