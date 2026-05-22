"""Pydantic schemas for dispatch ingestion API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.dispatch import AdaptiveCardDispatch, DispatchStatus


class DispatchCreateRequest(BaseModel):
	"""Incoming payload for adaptive card dispatch requests."""

	model_config = ConfigDict(populate_by_name=True)

	team_id: str = Field(min_length=1, max_length=128, alias="teamId")
	channel_id: str = Field(min_length=1, max_length=128, alias="channelId")
	reply_to_message_id: str = Field(min_length=1, max_length=128, alias="replyToMessageId")
	adaptive_card: dict[str, Any] = Field(alias="adaptiveCard")
	correlation_id: str = Field(min_length=1, max_length=128, alias="correlationId")


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
