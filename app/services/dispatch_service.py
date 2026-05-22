"""Business logic for dispatch ingestion and idempotency."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dispatch import AdaptiveCardDispatch
from app.repositories.dispatch_repository import DispatchRepository
from app.schemas.dispatch import DispatchCreateRequest
from app.services.graph_client import GraphApiError, GraphClient

logger = logging.getLogger(__name__)


class DispatchService:
	"""Coordinate repository operations for dispatch creation."""

	def __init__(self, session: Session, repository: DispatchRepository) -> None:
		self._session = session
		self._repository = repository

	def create_or_get_dispatch(
		self,
		payload: DispatchCreateRequest,
	) -> tuple[AdaptiveCardDispatch, bool]:
		"""Create a pending record or return an existing one for the same correlation id."""

		existing = self._repository.get_by_correlation_id(self._session, payload.correlation_id)
		if existing is not None:
			return existing, False

		try:
			created = self._repository.create_pending_dispatch(
				self._session,
				correlation_id=payload.correlation_id,
				team_id=payload.team_id,
				channel_id=payload.channel_id,
				reply_to_message_id=payload.reply_to_message_id,
				adaptive_card=payload.adaptive_card,
			)
			self._session.commit()
			return created, True
		except IntegrityError:
			# Another request could have inserted the same correlation id concurrently.
			self._session.rollback()
			replay = self._repository.get_by_correlation_id(self._session, payload.correlation_id)
			if replay is None:
				raise
			return replay, False


class DispatchProcessingService:
	"""Worker-facing service to process pending dispatch records sequentially."""

	def __init__(
		self,
		session: Session,
		repository: DispatchRepository,
		*,
		graph_client: GraphClient,
		max_retries: int,
	) -> None:
		self._session = session
		self._repository = repository
		self._graph_client = graph_client
		self._max_retries = max_retries

	def process_pending_batch(self, *, batch_size: int) -> int:
		"""Process one batch of due pending records and return processed count."""

		now = datetime.now(timezone.utc)
		pending = self._repository.list_due_pending_dispatches(
			self._session,
			now=now,
			limit=batch_size,
		)
		for dispatch in pending:
			self._process_single_dispatch(dispatch)
		return len(pending)

	def _process_single_dispatch(self, dispatch: AdaptiveCardDispatch) -> None:
		"""Run state machine for a single dispatch record."""

		try:
			self._repository.mark_processing(dispatch)
			self._session.commit()

			result = self._graph_client.send_adaptive_card_reply(
				team_id=dispatch.team_id,
				channel_id=dispatch.channel_id,
				reply_to_message_id=dispatch.reply_to_message_id,
				adaptive_card=dispatch.adaptive_card_json,
			)
			self._repository.mark_sent(
				dispatch,
				graph_message_id=result.graph_message_id,
				sent_at=datetime.now(timezone.utc),
			)
			self._session.commit()
			logger.info(
				"Dispatch sent",
				extra={
					"correlation_id": dispatch.correlation_id,
					"dispatch_id": dispatch.id,
				},
			)
		except GraphApiError as exc:
			self._handle_failure(dispatch=dispatch, error_message=str(exc), retriable=exc.retriable)
		except Exception as exc:
			self._handle_failure(dispatch=dispatch, error_message=str(exc), retriable=True)

	def _handle_failure(self, *, dispatch: AdaptiveCardDispatch, error_message: str, retriable: bool) -> None:
		"""Persist retry or failed transition when Graph call fails."""

		self._session.rollback()
		refreshed = self._repository.get_by_id(self._session, dispatch.id)
		if refreshed is None:
			logger.error(
				"Dispatch missing during failure handling",
				extra={"dispatch_id": dispatch.id, "correlation_id": dispatch.correlation_id},
			)
			return

		next_retry_count = refreshed.retry_count + 1
		should_fail = next_retry_count >= self._max_retries
		if should_fail:
			self._repository.mark_failed(
				refreshed,
				retry_count=next_retry_count,
				last_error=error_message,
			)
		else:
			delay_seconds = calculate_retry_delay_seconds(next_retry_count)
			next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
			self._repository.mark_pending_retry(
				refreshed,
				retry_count=next_retry_count,
				next_attempt_at=next_attempt_at,
				last_error=error_message,
			)

		self._session.commit()
		logger.warning(
			"Dispatch send failed",
			extra={
				"dispatch_id": refreshed.id,
				"correlation_id": refreshed.correlation_id,
				"retry_count": refreshed.retry_count,
				"retriable": retriable,
				"final_status": refreshed.status.value,
			},
		)


def calculate_retry_delay_seconds(retry_count: int) -> int:
	"""Return exponential backoff delay capped at five minutes."""

	base_delay = 5
	delay = base_delay * (2 ** max(retry_count - 1, 0))
	return min(delay, 300)
