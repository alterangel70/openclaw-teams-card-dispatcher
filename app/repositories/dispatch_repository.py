"""Repository methods for adaptive card dispatch persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dispatch import AdaptiveCardDispatch, DispatchStatus


class DispatchRepository:
	"""Encapsulate database operations for dispatch records."""

	def get_by_correlation_id(
		self,
		session: Session,
		correlation_id: str,
	) -> AdaptiveCardDispatch | None:
		"""Fetch a dispatch record by correlation id if it exists."""

		statement = select(AdaptiveCardDispatch).where(
			AdaptiveCardDispatch.correlation_id == correlation_id,
		)
		return session.execute(statement).scalar_one_or_none()

	def create_pending_dispatch(
		self,
		session: Session,
		*,
		correlation_id: str,
		team_id: str,
		channel_id: str,
		reply_to_message_id: str,
		adaptive_card: dict,
	) -> AdaptiveCardDispatch:
		"""Create a new pending dispatch record."""

		dispatch = AdaptiveCardDispatch(
			correlation_id=correlation_id,
			team_id=team_id,
			channel_id=channel_id,
			reply_to_message_id=reply_to_message_id,
			adaptive_card_json=adaptive_card,
			status=DispatchStatus.PENDING,
			retry_count=0,
		)
		session.add(dispatch)
		session.flush()
		session.refresh(dispatch)
		return dispatch
