"""Business logic for dispatch ingestion and idempotency."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dispatch import AdaptiveCardDispatch
from app.repositories.dispatch_repository import DispatchRepository
from app.schemas.dispatch import DispatchCreateRequest


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
