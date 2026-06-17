"""Azure Teams Bot delivery client for proactive adaptive card messaging."""

from __future__ import annotations

from http import HTTPStatus

import httpx

from app.services.delivery_client import DeliveryResult
from app.services.token_provider import AccessTokenProvider


class TeamsBotClient:
    """Send adaptive cards through Bot Framework so messages come from the bot identity."""

    def __init__(
        self,
        token_provider: AccessTokenProvider,
        *,
        service_url: str,
        bot_app_id: str,
        bot_name: str,
        timeout_seconds: int = 20,
    ) -> None:
        if not service_url:
            raise ValueError("TEAMS_SERVICE_URL (or BOT_SERVICE_URL) is required")
        if not bot_app_id:
            raise ValueError("BOT_APP_ID is required")

        self._token_provider = token_provider
        self._service_url = service_url.rstrip("/")
        self._bot_app_id = bot_app_id
        self._bot_name = bot_name
        self._timeout_seconds = timeout_seconds

    def build_channel_activity_payload(
        self,
        *,
        team_id: str,
        channel_id: str,
        conversation_id: str,
        reply_to_message_id: str,
        adaptive_card: dict,
    ) -> dict:
        """Build a Bot Framework activity payload for a channel thread reply."""

        return {
            "type": "message",
            "replyToId": reply_to_message_id,
            "from": {
                "id": self._bot_app_id,
                "name": self._bot_name,
            },
            "conversation": {
                "id": conversation_id,
            },
            "channelData": {
                "channel": {
                    "id": channel_id,
                },
                "team": {
                    "id": team_id,
                },
            },
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": adaptive_card,
                },
            ],
        }

    def build_dm_activity_payload(
        self,
        *,
        conversation_id: str,
        adaptive_card: dict,
    ) -> dict:
        """Build a Bot Framework activity payload for a direct message."""

        return {
            "type": "message",
            "from": {
                "id": self._bot_app_id,
                "name": self._bot_name,
            },
            "conversation": {
                "id": conversation_id,
            },
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": adaptive_card,
                },
            ],
        }

    # Keep old name as a forwarding alias so existing call-sites outside the
    # service layer (e.g. manual scripts) don't break immediately.
    def build_activity_payload(
        self,
        *,
        team_id: str,
        channel_id: str,
        conversation_id: str,
        reply_to_message_id: str,
        adaptive_card: dict,
    ) -> dict:
        """Build a Bot Framework activity payload containing adaptive card attachment."""

        return self.build_channel_activity_payload(
            team_id=team_id,
            channel_id=channel_id,
            conversation_id=conversation_id,
            reply_to_message_id=reply_to_message_id,
            adaptive_card=adaptive_card,
        )

    def send_adaptive_card(
        self,
        *,
        conversation_type: str,
        conversation_id: str,
        adaptive_card: dict,
        team_id: str | None = None,
        channel_id: str | None = None,
        reply_to_message_id: str | None = None,
    ) -> DeliveryResult:
        """Send adaptive card via Bot Framework.

        Routes to a channel thread reply or a direct message depending on
        ``conversation_type``.  For ``"channel"`` the caller must supply
        ``team_id``, ``channel_id``, and ``reply_to_message_id``.
        """

        if conversation_type == "dm":
            return self._send_dm(
                conversation_id=conversation_id,
                adaptive_card=adaptive_card,
            )

        if team_id is None or channel_id is None or reply_to_message_id is None:
            return DeliveryResult(
                success=False,
                error_message=(
                    "team_id, channel_id and reply_to_message_id are required"
                    " for channel dispatches"
                ),
                retriable=False,
            )

        return self._send_channel_reply(
            team_id=team_id,
            channel_id=channel_id,
            conversation_id=conversation_id,
            reply_to_message_id=reply_to_message_id,
            adaptive_card=adaptive_card,
        )

    def _send_channel_reply(
        self,
        *,
        team_id: str,
        channel_id: str,
        conversation_id: str,
        reply_to_message_id: str,
        adaptive_card: dict,
    ) -> DeliveryResult:
        """POST adaptive card as a thread reply to an existing Teams activity."""

        token = self._token_provider.get_access_token()
        # The conversation_id already encodes the thread via its ;messageid=xxx
        # suffix.  Using that as the conversation endpoint (without a trailing
        # activity-id path segment) is the correct Teams Bot Framework pattern
        # for posting a reply into an existing channel thread.
        url = f"{self._service_url}/v3/conversations/{conversation_id}/activities"
        payload = self.build_channel_activity_payload(
            team_id=team_id,
            channel_id=channel_id,
            conversation_id=conversation_id,
            reply_to_message_id=reply_to_message_id,
            adaptive_card=adaptive_card,
        )
        return self._post_activity(url=url, token=token, payload=payload)

    def _send_dm(
        self,
        *,
        conversation_id: str,
        adaptive_card: dict,
    ) -> DeliveryResult:
        """POST adaptive card to a direct-message conversation."""

        token = self._token_provider.get_access_token()
        url = f"{self._service_url}/v3/conversations/{conversation_id}/activities"
        payload = self.build_dm_activity_payload(
            conversation_id=conversation_id,
            adaptive_card=adaptive_card,
        )
        return self._post_activity(url=url, token=token, payload=payload)

    def _post_activity(self, *, url: str, token: str, payload: dict) -> DeliveryResult:
        """Execute the HTTP POST to the Bot Framework connector and normalise the result."""

        headers = {
            "Authorization": f"Bearer {token}",
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
            return DeliveryResult(
                success=False,
                error_message=f"Network error calling Bot Framework: {exc}",
                retriable=True,
            )

        if response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.ACCEPTED):
            activity_id = None
            try:
                body = response.json()
                if isinstance(body, dict):
                    activity_id = body.get("id")
            except ValueError:
                activity_id = None

            return DeliveryResult(
                success=True,
                message_id=str(activity_id) if activity_id else None,
            )

        return DeliveryResult(
            success=False,
            error_message=self._extract_error_message(response),
            retriable=self._is_retriable_status(response.status_code),
        )

    @staticmethod
    def _is_retriable_status(status_code: int) -> bool:
        """Return whether a response status is retryable for bot delivery."""

        if status_code in (HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.REQUEST_TIMEOUT):
            return True
        if status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            return True
        return status_code >= 500

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """Extract readable error text from connector response."""

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
