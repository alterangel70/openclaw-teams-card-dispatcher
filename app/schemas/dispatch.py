"""Pydantic schemas for dispatch ingestion API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.dispatch import AdaptiveCardDispatch, DispatchStatus

ConversationType = Literal["channel", "dm"]

# Strips the outer Bot Framework conversation reference wrapper that callers
# sometimes pass instead of the bare channel/DM ID.  Only the "conversation:"
# prefix is removed; the ";messageid=<id>" suffix is intentionally preserved
# because Teams uses it to route the message to the correct thread:
#   "conversation:19:xxx@thread.tacv2;messageid=123"  →  "19:xxx@thread.tacv2;messageid=123"
_RE_STRIP_PREFIX = re.compile(r"^conversation:")

# Accepted Teams conversation ID shapes after normalization:
#   19:xxx@thread.tacv2[;messageid=digits]   (channel or channel-thread)
#   a:xxx                                    (bot DM activity reference — activity.conversation.id)
#
# NOTE: 8:orgid:xxx is activity.from.id (AAD user identity), NOT a conversation
# reference. The Bot Framework returns 400 when it is used as a conversation ID.
# It is intentionally excluded from this validator.
_RE_VALID_CONVERSATION_ID = re.compile(
    r"^("
    r"19:[A-Za-z0-9_\-]+@thread\.[A-Za-z0-9\.]+(;messageid=\d+)?"
    r"|a:[A-Za-z0-9_\-]+"
    r")$"
)


class DispatchCreateRequest(BaseModel):
	"""Incoming payload for adaptive card dispatch requests.

	For ``conversationType="channel"`` the fields ``teamId``, ``channelId``,
	and ``replyToMessageId`` are required.  For ``conversationType="dm"`` they
	are ignored and may be omitted entirely.
	"""

	model_config = ConfigDict(populate_by_name=True)

	conversation_type: ConversationType = Field(alias="conversationType")
	conversation_id: str = Field(min_length=1, max_length=512, alias="conversationId")
	adaptive_card: dict[str, Any] = Field(alias="adaptiveCard")
	correlation_id: str = Field(min_length=1, max_length=128, alias="correlationId")

	# Channel-only fields — required when conversation_type == "channel".
	team_id: str | None = Field(default=None, max_length=128, alias="teamId")
	channel_id: str | None = Field(default=None, max_length=128, alias="channelId")
	reply_to_message_id: str | None = Field(default=None, max_length=128, alias="replyToMessageId")

	@field_validator("conversation_id", mode="before")
	@classmethod
	def _normalize_conversation_id(cls, v: object) -> str:
		"""Strip Bot Framework wrapper and validate the resulting ID.

		Accepted input examples:
		  - "19:xxx@thread.tacv2"                          (already clean)
		  - "conversation:19:xxx@thread.tacv2;messageid=1" (from BF activity ref)
		  - "a:xxx"                                        (bot DM — activity.conversation.id)
		
		NOT accepted: "8:orgid:xxx" — that is activity.from.id (AAD user identity),
		not a Bot Framework conversation reference. Use activity.conversation.id instead.
		"""
		if not isinstance(v, str):
			raise ValueError("conversationId must be a string")

		cleaned = _RE_STRIP_PREFIX.sub("", v)

		if not _RE_VALID_CONVERSATION_ID.match(cleaned):
			raise ValueError(
				f"conversationId is not a recognised Teams conversation ID "
				f"(received: '{v}', after normalisation: '{cleaned}'). "
			"Expected a channel thread ID (19:…@thread.tacv2) "
			"or a bot DM conversation reference (a:…). "
			"Note: 8:orgid:… is the AAD user identity (activity.from.id), not a conversation ID — "
			"use activity.conversation.id instead."
			)

		return cleaned

	@model_validator(mode="after")
	def _require_channel_fields_for_channel_type(self) -> "DispatchCreateRequest":
		if self.conversation_type == "channel":
			missing = [
				alias
				for field_name, alias in (
					("team_id", "teamId"),
					("channel_id", "channelId"),
					("reply_to_message_id", "replyToMessageId"),
				)
				if getattr(self, field_name) is None
			]
			if missing:
				raise ValueError(
					f"Fields {missing} are required when conversationType is 'channel'"
				)
		return self


class DispatchResponse(BaseModel):
	"""API response payload for created or replayed dispatches."""

	model_config = ConfigDict(populate_by_name=True)

	id: int
	correlation_id: str = Field(alias="correlationId")
	status: DispatchStatus
	retry_count: int = Field(alias="retryCount")
	created_at: datetime = Field(alias="createdAt")
	updated_at: datetime = Field(alias="updatedAt")

	@classmethod
	def from_model(cls, dispatch: AdaptiveCardDispatch) -> "DispatchResponse":
		"""Build response payload from ORM model instance."""

		return cls(
			id=dispatch.id,
			correlationId=dispatch.correlation_id,
			status=dispatch.status,
			retryCount=dispatch.retry_count,
			createdAt=dispatch.created_at,
			updatedAt=dispatch.updated_at,
		)
