"""Microsoft Graph client for sending adaptive card replies in Teams channels."""

from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus

import httpx

from app.services.token_provider import AccessTokenProvider


@dataclass(frozen=True)
class GraphSendResult:
	"""Normalized successful Graph send response."""

	graph_message_id: str


class GraphApiError(Exception):
	"""Exception raised when Graph returns an unsuccessful response."""

	def __init__(self, message: str, *, retriable: bool, status_code: int | None = None) -> None:
		super().__init__(message)
		self.retriable = retriable
		self.status_code = status_code


class GraphClient:
	"""HTTP client wrapper to post adaptive cards as replies via Graph API."""

	def __init__(
		self,
		token_provider: AccessTokenProvider,
		*,
		timeout_seconds: int = 20,
		base_url: str = "https://graph.microsoft.com/v1.0",
	) -> None:
		self._token_provider = token_provider
		self._timeout_seconds = timeout_seconds
		self._base_url = base_url.rstrip("/")

	def send_adaptive_card_reply(
		self,
		*,
		team_id: str,
		channel_id: str,
		reply_to_message_id: str,
		adaptive_card: dict,
	) -> GraphSendResult:
		"""Send adaptive card to a Teams channel message reply thread."""

		access_token = self._token_provider.get_access_token()
		url = (
			f"{self._base_url}/teams/{team_id}/channels/{channel_id}"
			f"/messages/{reply_to_message_id}/replies"
		)

		payload = {
			"body": {
				"contentType": "html",
				"content": "<attachment id=\"adaptive-card\"></attachment>",
			},
			"attachments": [
				{
					"id": "adaptive-card",
					"contentType": "application/vnd.microsoft.card.adaptive",
					"content": json.dumps(adaptive_card, ensure_ascii=True),
				},
			],
		}

		headers = {
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json",
		}

		try:
			response = httpx.post(
				url,
				headers=headers,
				json=payload,
				timeout=self._timeout_seconds,
			)
		except httpx.RequestError as exc:
			raise GraphApiError(f"Network error calling Graph: {exc}", retriable=True) from exc

		if response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
			data = response.json()
			message_id = data.get("id")
			if not message_id:
				raise GraphApiError(
					"Graph response does not include message id",
					retriable=False,
					status_code=response.status_code,
				)
			return GraphSendResult(graph_message_id=str(message_id))

		retriable = self._is_retriable_status(response.status_code)
		error_text = self._extract_error_message(response)
		raise GraphApiError(
			f"Graph request failed: {error_text}",
			retriable=retriable,
			status_code=response.status_code,
		)

	@staticmethod
	def _is_retriable_status(status_code: int) -> bool:
		"""Return whether a Graph status code should be retried later."""

		if status_code in (HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.REQUEST_TIMEOUT):
			return True
		if status_code >= 500:
			return True
		if status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
			return True
		return False

	@staticmethod
	def _extract_error_message(response: httpx.Response) -> str:
		"""Extract a readable error from Graph response payload."""

		try:
			payload = response.json()
		except ValueError:
			return response.text or f"HTTP {response.status_code}"

		if isinstance(payload, dict):
			error = payload.get("error")
			if isinstance(error, dict):
				return str(error.get("message") or error.get("code") or payload)
			return str(payload)
		return str(payload)
