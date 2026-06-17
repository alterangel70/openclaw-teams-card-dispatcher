"""Repository methods for adaptive card dispatch persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
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

	def get_by_id(self, session: Session, dispatch_id: int) -> AdaptiveCardDispatch | None:
		"""Fetch a dispatch record by database id."""

		statement = select(AdaptiveCardDispatch).where(AdaptiveCardDispatch.id == dispatch_id)
		return session.execute(statement).scalar_one_or_none()

	def list_due_pending_dispatches(
		self,
		session: Session,
		*,
		now: datetime,
		limit: int,
	) -> list[AdaptiveCardDispatch]:
		"""Return pending dispatches that are eligible for processing."""

		statement = (
			select(AdaptiveCardDispatch)
			.where(AdaptiveCardDispatch.status == DispatchStatus.PENDING)
			.where(
				or_(
					AdaptiveCardDispatch.next_attempt_at.is_(None),
					AdaptiveCardDispatch.next_attempt_at <= now,
				),
			)
			.order_by(AdaptiveCardDispatch.created_at.asc())
			.limit(limit)
		)
		return list(session.execute(statement).scalars().all())

	def create_pending_dispatch(
		self,
		session: Session,
		*,
		correlation_id: str,
		conversation_type: str,
		conversation_id: str,
		adaptive_card: dict,
		team_id: str | None = None,
		channel_id: str | None = None,
		reply_to_message_id: str | None = None,
	) -> AdaptiveCardDispatch:
		"""Create a new pending dispatch record."""

		dispatch = AdaptiveCardDispatch(
			correlation_id=correlation_id,
			conversation_type=conversation_type,
			team_id=team_id,
			channel_id=channel_id,
			conversation_id=conversation_id,
			reply_to_message_id=reply_to_message_id,
			adaptive_card_json=adaptive_card,
			status=DispatchStatus.PENDING,
			retry_count=0,
		)
		session.add(dispatch)
		session.flush()
		session.refresh(dispatch)
		return dispatch

	def mark_processing(self, dispatch: AdaptiveCardDispatch) -> None:
		"""Set record state to PROCESSING before delivery call."""

		dispatch.status = DispatchStatus.PROCESSING
		dispatch.last_error = None

	def mark_sent(
		self,
		dispatch: AdaptiveCardDispatch,
		*,
		graph_message_id: str | None,
		sent_at: datetime,
	) -> None:
		"""Set record state to SENT when delivery succeeds."""

		dispatch.status = DispatchStatus.SENT
		dispatch.graph_message_id = graph_message_id
		dispatch.sent_at = sent_at
		dispatch.next_attempt_at = None
		dispatch.last_error = None

	def mark_pending_retry(
		self,
		dispatch: AdaptiveCardDispatch,
		*,
		retry_count: int,
		next_attempt_at: datetime,
		last_error: str,
	) -> None:
		"""Set record state to PENDING for another retry cycle."""

		dispatch.status = DispatchStatus.PENDING
		dispatch.retry_count = retry_count
		dispatch.next_attempt_at = next_attempt_at
		dispatch.last_error = last_error

	def mark_failed(self, dispatch: AdaptiveCardDispatch, *, retry_count: int, last_error: str) -> None:
		"""Set record state to FAILED after reaching max retries."""

		dispatch.status = DispatchStatus.FAILED
		dispatch.retry_count = retry_count
		dispatch.last_error = last_error
		dispatch.next_attempt_at = None
